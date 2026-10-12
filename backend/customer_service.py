"""Customer service agent — drafts messages for customers.

Writes clear, friendly replies to customers based on what the other agents find,
and saves them as drafts for a human to review and send. It never emails anyone.
"""

from agent_base import RoleSpec

SPEC = RoleSpec(
    name="customer_service",
    title="Customer Service",
    prompt_file="customer_service.md",
    summary="Drafts customer messages (drafts only — never sends).",
)
