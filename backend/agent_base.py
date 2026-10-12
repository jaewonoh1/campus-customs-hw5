"""Shared machinery for building a Campus Customs agent.

Each of the five roles is defined by a small `RoleSpec` in its own file
(`boss.py`, `inventory.py`, …). `build_agent` turns a spec into a PydanticAI
agent: it loads the role's prompt, adds a dynamic instruction with the current
roster and ticket, and gives the agent one delegation tool (`delegate_to`) so it
can hand work to any teammate — full connectivity across the team.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic_ai import Agent, ModelRetry, RunContext

from config import MODEL_SETTINGS, PROMPTS_DIR, make_model
from models import Deps

# Stop runaway hand-offs: how deep a delegation chain may go (0 = boss).
MAX_DELEGATION_DEPTH = 4


@dataclass(frozen=True)
class RoleSpec:
    """One agent role. Lives in that role's own file to keep the five clear."""

    name: str          # machine key, e.g. "inventory"
    title: str         # display name, e.g. "Inventory"
    prompt_file: str   # file under backend/prompts/, e.g. "inventory.md"
    summary: str       # one line teammates see in the roster, for delegation


def _load_prompt(prompt_file: str) -> str:
    return (PROMPTS_DIR / prompt_file).read_text(encoding="utf-8")


def build_agent(spec: RoleSpec, toolset) -> Agent[Deps, str]:
    """Build the agent for one role, sharing the given MCP toolset."""
    agent: Agent[Deps, str] = Agent(
        make_model(),
        deps_type=Deps,
        output_type=str,
        instructions=_load_prompt(spec.prompt_file),
        toolsets=[toolset],
        model_settings=MODEL_SETTINGS,
    )

    @agent.instructions
    def whoami(ctx: RunContext[Deps]) -> str:
        roster = ctx.deps.team.roster_text(exclude=spec.name)
        lines = [
            f"You are the {spec.title} agent (role key: {spec.name}).",
            "Your teammates (delegate with delegate_to(role, task)):",
            roster,
        ]
        if ctx.deps.ticket_id is not None:
            lines.append(
                f"You are working ticket #{ctx.deps.ticket_id}. Use get_ticket "
                "to see its details and update_ticket_status as it progresses."
            )
        return "\n".join(lines)

    @agent.tool
    async def delegate_to(ctx: RunContext[Deps], role: str, task: str) -> str:
        """Hand a sub-task to a teammate and get their answer back.

        `role` is one of the team role keys (boss, inventory, accounting,
        facilities, customer_service). `task` is a clear, self-contained
        instruction. Delegate when the work needs a teammate's area; do work you
        own yourself, and don't bounce the same task back and forth.
        """
        role = role.strip().lower()
        team = ctx.deps.team
        if role not in team.registry:
            raise ModelRetry(
                f"Unknown role '{role}'. Valid roles: {sorted(team.registry)}."
            )
        if role == spec.name:
            raise ModelRetry("That's your own role — handle it yourself.")
        if role in ctx.deps.chain:
            return (
                f"[{role} is already working above you in this chain — avoid a loop; "
                "summarize what you need instead.]"
            )
        if ctx.deps.depth >= MAX_DELEGATION_DEPTH:
            return (
                "[delegation depth limit reached — handle it yourself or report "
                "what still needs doing.]"
            )
        return await team.run_role(
            role,
            task,
            ticket_id=ctx.deps.ticket_id,
            depth=ctx.deps.depth + 1,
            parent_run_id=ctx.deps.run_id,
            chain=ctx.deps.chain + (spec.name,),
        )

    return agent
