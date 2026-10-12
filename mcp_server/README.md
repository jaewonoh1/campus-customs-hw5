# Campus Customs MCP server

The one place the agent team gets its tools. Every agent in this homework — boss,
inventory, accounting, facilities, customer service — reaches the shop's data
only through this **FastMCP** server (`server.py`, server name `campus-customs`),
so there is a single, auditable surface for reading and (in later problems)
changing shop state.

## Database file

The server talks to the **working copy**:

```
data/campus_customs_new.db
```

This is the copy that later problems update; the original `data/campus_customs.db`
is kept untouched as a reference and for resetting before a full run. The path is
resolved relative to `server.py`, so the server finds the database no matter where
it is launched from.

All tools so far are **read-only** and only return rows that actually exist in the
database — they never invent data. When nothing matches, a tool returns an empty
list or `None` rather than a fabricated value.

## Tools

Grouped by what they do. Reads return rows exactly as stored and never invent
data (a miss returns `[]` / `None` / `{"error": ...}`). Prepare/act tools change
the working copy. The reserved `pay` tool is **not** given to the agents.

### Reads

| tool | table(s) | returns |
|---|---|---|
| `get_today()` | `desk` | the shop's `date_today` + notes — the "today" for all overdue checks |
| `list_open_tickets()` | `tickets` | every open ticket, newest first, with its `sku`/`size`/`qty`/`lease_id`/`invoice_id` links |
| `get_ticket(ticket_id)` | `tickets` | one ticket (any status), or `None` |
| `check_stock(sku, size?)` | `inventory` | on-hand `qty` (+ name, location); one size or all — empty if not stocked |
| `get_pricing(sku)` | `pricing` | `unit_cost`, `list_price`, plus derived `margin` / `margin_pct`; `None` if none |
| `list_vendors()` | `vendors` | all vendors with `specialty` and `lead_days` (the authoritative lead time) |
| `list_invoices(status?)` | `invoices` | invoices, optionally filtered (e.g. `open` = unpaid) |
| `vendor_has_open_invoice(vendor_id)` | `invoices` | whether a vendor is blocked from shipping by an open unpaid invoice |
| `get_cash_balance(account='checking')` | `cash_accounts` | current balance; `None` if the account is unknown |
| `list_leases()` | `leases` | all leases: space, landlord, `monthly_rent`, `next_due` |
| `get_lease(lease_id)` | `leases` | one lease, or `None` |

### Prepare / act (change the working copy)

| tool | table(s) | effect |
|---|---|---|
| `update_ticket_status(ticket_id, status, note?)` | `tickets` | move a ticket forward and append a dated note |
| `prepare_purchase_order(ticket_id, sku, qty, vendor_id, size?)` | `purchase_orders` (reads `pricing`, `vendors`, `invoices`) | record a PO **pending human approval**, with cost/ETA and a `blocked_reason` if the vendor has an unpaid invoice — does not order or ship |
| `prepare_payment(ticket_id, kind, amount, ref_id?)` | `payment_requests` (reads `cash_accounts`) | record a payment **pending human approval**, with an `affordable` flag — moves no money |
| `save_customer_message(ticket_id, body, recipient?)` | `customer_messages` | save a customer reply as a **draft** — never emailed |

### Reserved — human-approval only (not exposed to agents)

| tool | table(s) | effect |
|---|---|---|
| `pay(approved_by, payment_request_id? \| kind/ref_id/amount, account?)` | `cash_accounts`, `payments`, `invoices`, `payment_requests` | execute a payment. Requires a human `approved_by`; **refuses if it would overdraw** (cash never goes negative); debits cash, logs the payment, marks a paid invoice `paid`. For the dashboard's approval step in a later problem. |

The `purchase_orders`, `payment_requests`, and `customer_messages` tables hold
agent-prepared artifacts awaiting a human; they are created on demand and cleared
when the database is reset.

See `../output/harness.md` for how the tools map to the three open tickets and to
each agent.

## Run (later problems)

```bash
fastmcp run mcp_server/server.py
```

Requires `fastmcp` (see the project `requirements.txt`).
