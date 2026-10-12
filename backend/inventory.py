"""Inventory agent — stock, shortfalls, and which vendor can restock.

Checks stock by SKU and size, spots shortfalls against what a ticket asks for,
and works out which vendor can restock (matching specialty and lead time), always
checking whether that vendor is blocked by an open unpaid invoice first.
"""

from agent_base import RoleSpec

SPEC = RoleSpec(
    name="inventory",
    title="Inventory",
    prompt_file="inventory.md",
    summary="Checks stock by sku/size, spots shortfalls, finds the right vendor to restock.",
)
