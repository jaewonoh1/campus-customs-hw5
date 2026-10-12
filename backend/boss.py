"""Boss agent — reads a ticket, routes it, makes the final call.

The team's entry point: the boss reads each open ticket, decides which
specialists should work it, delegates, and then issues a clear final decision
(what was done, what is prepared, and what still needs human approval).
"""

from agent_base import RoleSpec

SPEC = RoleSpec(
    name="boss",
    title="Boss",
    prompt_file="boss.md",
    summary="Reads tickets, decides who works them, makes the final call.",
)
