"""Typed data shapes for the Campus Customs agent team.

Shop facts (tickets, stock, prices, cash, …) are read as plain dicts straight
from the MCP tools, so they are not re-modelled here. These types are the
team-side shapes: the per-run context the agents share, and the audit records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:  # avoid a runtime import cycle with team.py
    from team import Team


@dataclass
class Deps:
    """Per-run context handed to an agent and its delegation tool.

    Carries the running `Team` (so the agent can delegate to any teammate), this
    run's id and role, the ticket being worked, and how deep in the delegation
    chain we are (to stop runaway hand-offs).
    """

    team: "Team"
    run_id: str
    role: str
    ticket_id: int | None = None
    depth: int = 0
    # roles already on the current delegation chain, to avoid A→B→A loops
    chain: tuple[str, ...] = field(default_factory=tuple)


# --- audit trail -----------------------------------------------------------


class AuditToolCall(BaseModel):
    """One tool invocation in an agent run, trimmed for the log."""

    tool: str = Field(description="MCP (or delegation) tool the agent called.")
    args: str = Field(description="Short string form of the arguments.")
    result: str = Field(description="Short string form of what the tool returned.")


class AuditEntry(BaseModel):
    """One agent loop step, appended to output/audit_trail.json (never wiped)."""

    timestamp: str = Field(description="UTC ISO-8601 time the step finished.")
    run_id: str = Field(description="Id of this agent run.")
    parent_run_id: str | None = Field(
        default=None, description="Run that delegated to this one; None for the boss."
    )
    ticket_id: int | None = Field(default=None, description="Ticket being worked.")
    agent: str = Field(description="Role that ran: boss/inventory/accounting/…")
    depth: int = Field(ge=0, description="Delegation depth (0 = boss entry point).")
    task: str = Field(description="The instruction this agent was given, truncated.")
    model: str = Field(description="Model used (gpt-6-luna).")
    tool_calls: list[AuditToolCall] = Field(
        default_factory=list, description="MCP tools called this step, in order."
    )
    delegations: list[str] = Field(
        default_factory=list, description="Roles this agent delegated to."
    )
    model_requests: int = Field(ge=0, description="Model calls during this step.")
    output: str = Field(description="The agent's answer, truncated.")
    stop_reason: str = Field(description="completed, usage_limit, or error: ...")
