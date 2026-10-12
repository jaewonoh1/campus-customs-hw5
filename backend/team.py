"""The Campus Customs agent team: five agents with full connectivity.

`Team` builds the five role agents over one shared MCP toolset, keeps a registry
so any agent can delegate to any other, runs an agent while recording an audit
step for each loop, and drives the work from the boss down.

Run the whole board (resets the working database first, as the shop rules
require):

    python backend/team.py                 # resolve every open ticket
    python backend/team.py --ticket 101    # resolve one ticket
    python backend/team.py --no-reset      # don't reset the database first
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import uuid
from pathlib import Path

from pydantic_ai.messages import ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_ai.usage import UsageLimits

import accounting
import audit
import boss
import customer_service
import facilities
import inventory
from agent_base import build_agent
from config import HW_DIR, MODEL_NAME
from mcp_integration import agent_toolset, build_toolset
from models import AuditEntry, AuditToolCall, Deps

# All five role specs, boss first (the entry point).
SPECS = [boss.SPEC, inventory.SPEC, accounting.SPEC, facilities.SPEC, customer_service.SPEC]

# A few model calls + tool calls per step, with headroom for a retry.
USAGE_LIMITS = UsageLimits(request_limit=10)

ORIGINAL_DB = HW_DIR / "data" / "campus_customs.db"
WORKING_DB = HW_DIR / "data" / "campus_customs_new.db"


def reset_database() -> None:
    """Copy the pristine database over the working copy (shop rule for a run)."""
    shutil.copyfile(ORIGINAL_DB, WORKING_DB)


class Team:
    """Holds the agents and runs them, with an audit step per agent loop."""

    def __init__(self) -> None:
        self._base_toolset = build_toolset()
        shared = agent_toolset(self._base_toolset)  # agents don't get `pay`
        self.specs = {spec.name: spec for spec in SPECS}
        self.registry = {spec.name: build_agent(spec, shared) for spec in SPECS}
        # guard against a pathological run spawning endless agent calls
        self.max_total_runs = 30
        self._runs = 0

    def roster_text(self, exclude: str | None = None) -> str:
        return "\n".join(
            f"  - {spec.name}: {spec.summary}"
            for spec in SPECS
            if spec.name != exclude
        )

    async def run_role(
        self,
        role: str,
        task: str,
        *,
        ticket_id: int | None,
        depth: int,
        parent_run_id: str | None,
        chain: tuple[str, ...] = (),
    ) -> str:
        """Run one agent on a task, record an audit step, return its answer."""
        self._runs += 1
        if self._runs > self.max_total_runs:
            return "[team run budget reached — stopping to protect token use.]"

        run_id = uuid.uuid4().hex[:8]
        deps = Deps(
            team=self, run_id=run_id, role=role, ticket_id=ticket_id,
            depth=depth, chain=chain,
        )
        agent = self.registry[role]

        stop_reason = "completed"
        output = ""
        new_messages: list = []
        try:
            result = await agent.run(task, deps=deps, usage_limits=USAGE_LIMITS)
            output = result.output
            new_messages = result.new_messages()
        except Exception as exc:  # noqa: BLE001 - logged, then surfaced to caller
            stop_reason = f"error: {type(exc).__name__}: {audit.shorten(exc, 150)}"
            output = f"[{role} could not finish: {stop_reason}]"

        tool_calls, delegations, model_requests = _extract(new_messages)
        try:
            audit.append_entry(
                AuditEntry(
                    timestamp=audit.utc_now(),
                    run_id=run_id,
                    parent_run_id=parent_run_id,
                    ticket_id=ticket_id,
                    agent=role,
                    depth=depth,
                    task=audit.shorten(task),
                    model=MODEL_NAME,
                    tool_calls=tool_calls,
                    delegations=delegations,
                    model_requests=model_requests,
                    output=audit.shorten(output),
                    stop_reason=stop_reason,
                )
            )
        except Exception:  # noqa: BLE001 - never fail a run over logging
            pass
        return output

    async def resolve_ticket(self, ticket_id: int) -> str:
        """Boss works a single ticket from the top."""
        task = (
            f"Resolve open ticket #{ticket_id}. Read it, decide who should handle "
            "it, delegate to the right teammates, and give a final decision: what "
            "was done, what you prepared, and what still needs human approval. "
            "Follow all shop rules."
        )
        return await self.run_role(
            "boss", task, ticket_id=ticket_id, depth=0, parent_run_id=None
        )

    async def run_open_tickets(self) -> dict[int, str]:
        """Resolve every open ticket, boss-first, returning each final decision."""
        async with self._base_toolset:
            tickets = await self._base_toolset.direct_call_tool("list_open_tickets", {})
            decisions: dict[int, str] = {}
            for t in tickets:
                decisions[t["id"]] = await self.resolve_ticket(t["id"])
            return decisions

    async def run_one(self, ticket_id: int) -> str:
        async with self._base_toolset:
            return await self.resolve_ticket(ticket_id)


def _extract(new_messages: list) -> tuple[list[AuditToolCall], list[str], int]:
    """Pull tool calls (with results), delegated roles, and model-call count."""
    returns_by_id: dict[str, object] = {}
    model_requests = 0
    for msg in new_messages:
        if isinstance(msg, ModelResponse):
            model_requests += 1
        for part in getattr(msg, "parts", []):
            if isinstance(part, ToolReturnPart):
                returns_by_id[part.tool_call_id] = part.content

    calls: list[AuditToolCall] = []
    delegations: list[str] = []
    for msg in new_messages:
        for part in getattr(msg, "parts", []):
            if isinstance(part, ToolCallPart):
                args = part.args_as_dict() if hasattr(part, "args_as_dict") else part.args
                if part.tool_name == "delegate_to":
                    role = ""
                    if isinstance(args, dict):
                        role = str(args.get("role", "")).strip().lower()
                    if role:
                        delegations.append(role)
                calls.append(
                    AuditToolCall(
                        tool=part.tool_name,
                        args=audit.shorten(args),
                        result=audit.shorten(returns_by_id.get(part.tool_call_id, "")),
                    )
                )
    return calls, delegations, model_requests


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Run the Campus Customs agent team.")
    parser.add_argument("--ticket", type=int, help="Resolve only this ticket id.")
    parser.add_argument(
        "--no-reset", action="store_true",
        help="Do not reset the working database before running.",
    )
    args = parser.parse_args()

    if not args.no_reset:
        reset_database()
        print(f"Reset working database from {ORIGINAL_DB.name}.")

    team = Team()
    if args.ticket is not None:
        decision = await team.run_one(args.ticket)
        print(f"\n=== Ticket #{args.ticket} ===\n{decision}")
    else:
        decisions = await team.run_open_tickets()
        for tid, decision in decisions.items():
            print(f"\n=== Ticket #{tid} ===\n{decision}")
    print(f"\nAudit trail: {audit.AUDIT_PATH}")


if __name__ == "__main__":
    asyncio.run(_main())
