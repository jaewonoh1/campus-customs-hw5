"""Facilities agent — the shop space: leases, rent, and what's due.

Handles the space side of the shop: reads leases, judges rent due or overdue
against the shop's today, and asks accounting to prepare the rent payment for
human approval.
"""

from agent_base import RoleSpec

SPEC = RoleSpec(
    name="facilities",
    title="Facilities",
    prompt_file="facilities.md",
    summary="Handles the shop space — leases, rent, due dates.",
)
