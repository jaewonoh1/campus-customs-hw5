"""Accounting agent — cash, invoices, margins, and approvals-in-waiting.

Watches cash and invoices, checks margins on price-override requests, and prepares
payments and purchase orders for human approval. Never moves money itself: it can
only prepare; the guarded `pay` tool (human approval) is out of its reach.
"""

from agent_base import RoleSpec

SPEC = RoleSpec(
    name="accounting",
    title="Accounting",
    prompt_file="accounting.md",
    summary="Watches cash & invoices, checks margins, prepares payments and POs for human approval.",
)
