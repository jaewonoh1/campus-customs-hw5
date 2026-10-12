# Campus Customs — System Harness

Living design doc for the Campus Customs Multi-Agent Operations system. Grows
problem by problem. Problem 2 covers the database; Problem 3 the MCP server;
Problem 5 the agent team, the grown tool set, audit, and safety.

The shop's "today" is **`desk.date_today`** (not the wall clock). In the current
data pack today is **2026-08-31**. Use it to decide what is overdue.

---

## Database

File: `data/campus_customs.db` (original, read-only reference).
Working copy: `data/campus_customs_new.db` (later problems update this one).

Nine tables. For each: its fields, then one line on why it matters to the agents.

### `desk`  — 1 row
| field | type | notes |
|---|---|---|
| `date_today` | TEXT | the shop's "today" (currently `2026-08-31`) |
| `notes` | TEXT | free notes |

Defines "now" for the whole shop; every overdue / due-soon decision reads this.

### `tickets`  — 3 rows (all `open`)
| field | type | notes |
|---|---|---|
| `id` | INTEGER PK | ticket number |
| `type` | TEXT | `customer_order`, `rent_notice`, `price_override` |
| `requester` | TEXT | who opened it |
| `subject` | TEXT | short title |
| `sku` | TEXT | links to `inventory.sku` / `pricing.sku` (nullable) |
| `size` | TEXT | links to `inventory.size` (nullable) |
| `qty` | INTEGER | quantity requested (nullable) |
| `lease_id` | INTEGER FK→`leases.id` | for rent/space tickets (nullable) |
| `invoice_id` | INTEGER FK→`invoices.id` | related vendor invoice (nullable) |
| `status` | TEXT | `open` / (resolved states later) |
| `notes` | TEXT | details |
| `created_at` | TEXT | ISO timestamp |

The work board. This is what the **boss** reads and routes; the FKs are how a
ticket reaches inventory, pricing, leases, and invoices.

### `inventory`  — 10 rows (PK: `sku` + `size`)
| field | type | notes |
|---|---|---|
| `sku` | TEXT | product code |
| `name` | TEXT | product name |
| `size` | TEXT | `S/M/L/XL` or `OS` |
| `qty` | INTEGER | units on hand |
| `location` | TEXT | aisle |

The **inventory** agent's source of truth for stock-by-size and shortfalls
(e.g. `CC-TEE-WHITE`/S = 0, `CC-MUG-CREST`/OS = 0).

### `vendors`  — 3 rows
| field | type | notes |
|---|---|---|
| `id` | INTEGER PK | vendor id |
| `name` | TEXT | vendor name |
| `specialty` | TEXT | what they supply (e.g. `apparel reprint`) |
| `lead_days` | INTEGER | restock lead time in days |

Who can restock what and how fast. `lead_days` is the authoritative lead time;
specialty tells inventory which vendor fits a given SKU.

### `pricing`  — 4 rows (PK: `sku`)
| field | type | notes |
|---|---|---|
| `sku` | TEXT | product code |
| `unit_cost` | REAL | what the shop pays |
| `list_price` | REAL | what the shop charges |

Lets **accounting** check margins and vet discount / price-override requests
(margin = `list_price − unit_cost`).

### `invoices`  — 1 row
| field | type | notes |
|---|---|---|
| `id` | INTEGER PK | invoice number |
| `vendor_id` | INTEGER FK→`vendors.id` | who billed us |
| `amount` | REAL | amount owed |
| `due_date` | TEXT | when it's due |
| `status` | TEXT | `open` (unpaid) / paid |
| `description` | TEXT | what it covers |

Money owed to vendors. Rule: **a vendor will not ship new product while it has
an open unpaid invoice** — so an open invoice can block a restock.

### `payments`  — 0 rows
| field | type | notes |
|---|---|---|
| `id` | INTEGER PK | payment id |
| `kind` | TEXT | what was paid (invoice, rent, …) |
| `ref_id` | INTEGER | id of the thing paid (invoice/lease) |
| `amount` | REAL | amount paid out |
| `account` | TEXT | source account (e.g. `checking`) |
| `paid_at` | TEXT | timestamp |
| `approved_by` | TEXT | **human** who approved |

Append-only record of cash going out. Written only after human approval; the
pay tool records here.

### `cash_accounts`  — 1 row (PK: `name`)
| field | type | notes |
|---|---|---|
| `name` | TEXT | account (`checking`) |
| `balance` | REAL | current cash (currently `3400.0`) |
| `date` | TEXT | as-of date |

The money guardrail: **pay must refuse if a payment would overdraw** (no
negative balances). Cash only goes out — nothing adds to it.

### `leases`  — 1 row
| field | type | notes |
|---|---|---|
| `id` | INTEGER PK | lease id |
| `space_name` | TEXT | the space (Chapel Street shop) |
| `landlord` | TEXT | Elm City Properties |
| `monthly_rent` | REAL | `2400.0` |
| `next_due` | TEXT | `2026-09-02` |
| `notes` | TEXT | free notes |

The **facilities** agent's data for rent/space: how much is due and when,
checked against `desk.date_today`.

---

## The three open tickets (and how they link)

**#101 — customer_order (Tauhid Zaman).** Wants `CC-TEE-WHITE` size **S**, qty 1.
- `inventory` CC-TEE-WHITE/S = **0** → shortfall; a restock is needed.
- `invoice_id` **501**: Bulldog Print Co (vendor 1, apparel reprint, 5-day lead)
  billed **$840** for a rush reprint of this exact tee, due **2026-08-28** →
  **overdue** (today 2026-08-31) and **open/unpaid**.
- Because the vendor won't ship with an open unpaid invoice, accounting must
  prepare payment of #501 (needs human approval; checking = $3,400) before
  inventory can restock the tee.

**#102 — rent_notice (Elm City Properties).** `lease_id` **1**.
- Lease 1: Chapel Street shop, rent **$2,400**, `next_due` **2026-09-02** (2 days
  out). Facilities handles the space side; accounting prepares the rent payment
  (human approval), and $2,400 fits within the $3,400 balance.

**#103 — price_override (Yale AI Club).** Wants **20** × `CC-HOOD-NAVY` size **M**.
- `inventory` CC-HOOD-NAVY/M = **8** → shortfall of 12 vs. the 20 requested;
  restock via Bulldog Print Co (apparel, 5-day lead).
- `pricing` CC-HOOD-NAVY: unit_cost **$22**, list **$58** (margin $36) → accounting
  vets whether a bulk discount still clears margin before the boss decides.

### Cross-cutting notes
- Cash is tight: #501 ($840) + rent ($2,400) = $3,240 against a $3,400 balance,
  so payment ordering matters and the no-negative-balance rule is live.
- Agents touched per ticket: #101 → inventory + accounting + customer service;
  #102 → facilities + accounting; #103 → inventory + accounting + customer
  service, with the boss making final calls on all three.

---

## MCP server (`mcp_server/`)

A **FastMCP** server (`mcp_server/server.py`, name `campus-customs`) is the one
place every agent gets tools — the single, auditable surface for the whole team.
It talks to the **working copy** `data/campus_customs_new.db`, and it is the only
shop-tools layer (no agent touches the database any other way). Tools never invent
data — a miss returns `[]` / `None` / `{"error": ...}`, not a fabricated row.

The three tools from Problem 3 (the ones the open tickets most clearly need):

| tool | table it reads | ticket it unlocks | why this tool is right for that ticket |
|---|---|---|---|
| `list_open_tickets()` | `tickets` (rows where `status='open'`, including the `sku`, `size`, `qty`, `lease_id`, `invoice_id` links) | **101, 102, 103** (all) | Nothing can be routed until the boss can see all three open tickets and the exact links each one carries — #101's `invoice_id=501`, #102's `lease_id=1`, #103's `sku=CC-HOOD-NAVY`/`qty=20` — so this is the entry point that turns each ticket into the follow-up lookups below. |
| `check_stock(sku, size?)` | `inventory` (the `qty` for a given `sku`+`size`) | **101** and **103** | Both tickets are a stock question before anything else — it reads `CC-TEE-WHITE`/S = 0 for #101 and `CC-HOOD-NAVY`/M = 8 against the 20 requested in #103 — so it is the tool that proves the shortfall that drives a restock decision. |
| `get_pricing(sku)` | `pricing` (`unit_cost` and `list_price` for a `sku`) | **103** | #103 asks for a bulk hoodie discount, and this tool returns `CC-HOOD-NAVY`'s cost ($22) and list ($58) with the derived margin ($36) so accounting can judge whether the discount still clears margin — the exact numbers the price-override call turns on. |

(#102 — the rent notice — is fully a `leases` lookup; its dedicated tool is added
in a later problem alongside the invoice/cash/payment tools.)

### Connection & smoke test (Problem 4)

The server is registered for the vibe coder in **`.mcp.json`** at the project root
(server name `campus-customs`, launched with the project `.venv` Python running
`mcp_server/server.py` over stdio). All three tools were called over the MCP
protocol using that exact connection; every output matched
`data/campus_customs_new.db` (tee S qty = 0; hoodie cost $22 / list $58 / margin
$36; open tickets 101, 102, 103). Evidence: **`output/mcp_smoke.json`**.

Note: the `command` path in `.mcp.json` is an absolute local path (this machine's
`.venv`); it will need adjusting when the repo is cloned elsewhere.

### Full MCP tool list (Problem 5) — tool → table

Grown so the agents can actually work the tickets. Every tool reads or writes only
`data/campus_customs_new.db`.

**Reads**

| tool | table(s) used |
|---|---|
| `get_today()` | `desk` |
| `list_open_tickets()` | `tickets` |
| `get_ticket(ticket_id)` | `tickets` |
| `check_stock(sku, size?)` | `inventory` |
| `get_pricing(sku)` | `pricing` |
| `list_vendors()` | `vendors` |
| `list_invoices(status?)` | `invoices` |
| `vendor_has_open_invoice(vendor_id)` | `invoices` |
| `get_cash_balance(account)` | `cash_accounts` |
| `list_leases()` | `leases` |
| `get_lease(lease_id)` | `leases` |

**Prepare / act** (write the working copy)

| tool | table(s) used |
|---|---|
| `update_ticket_status(ticket_id, status, note?)` | `tickets` |
| `prepare_purchase_order(ticket_id, sku, qty, vendor_id, size?)` | `purchase_orders` (reads `pricing`, `vendors`, `invoices`) |
| `prepare_payment(ticket_id, kind, amount, ref_id?)` | `payment_requests` (reads `cash_accounts`) |
| `save_customer_message(ticket_id, body, recipient?)` | `customer_messages` |

**Reserved — human approval only (not given to agents)**

| tool | table(s) used |
|---|---|
| `pay(approved_by, …)` | `cash_accounts`, `payments`, `invoices`, `payment_requests` |

`purchase_orders`, `payment_requests`, and `customer_messages` are agent-prepared
artifacts awaiting a human; created on demand, cleared on database reset.

---

## The agent team (`backend/`)

Five PydanticAI agents, each a clear role in its own file, all using **only** the
MCP tools above. Every agent runs on **gpt-6-luna** through the Portkey gateway
(`PORTKEY_API_KEY`); `gpt-6-luna` needs `reasoning_effort='none'` to use tools, so
that is set for all of them. The team has **full connectivity** — any agent can
`delegate_to(role, task)` any other — and the **boss** is the entry point.

| agent | file / prompt | what it does | typical MCP tools |
|---|---|---|---|
| **boss** | `boss.py` / `prompts/boss.md` | reads a ticket, routes it to specialists, makes the final call | `get_ticket`, `list_open_tickets`, `update_ticket_status`, `delegate_to` |
| **inventory** | `inventory.py` / `prompts/inventory.md` | checks stock by sku/size, spots shortfalls, finds which vendor can restock (specialty + lead time), checks the unpaid-invoice block | `check_stock`, `list_vendors`, `vendor_has_open_invoice`, `get_today` |
| **accounting** | `accounting.py` / `prompts/accounting.md` | watches cash & invoices, checks margins, prepares payments and POs for human approval | `get_cash_balance`, `list_invoices`, `get_pricing`, `prepare_payment`, `prepare_purchase_order` |
| **facilities** | `facilities.py` / `prompts/facilities.md` | the shop space: leases, rent, due dates; asks accounting to prepare rent | `list_leases`, `get_lease`, `get_today`, `delegate_to` |
| **customer_service** | `customer_service.py` / `prompts/customer_service.md` | drafts customer messages (drafts only, never sent) | `save_customer_message`, `delegate_to` |

Supporting code: `config.py` (model + Portkey + the gpt-6-luna guard),
`mcp_integration.py` (one shared toolset; hides `pay` from agents),
`agent_base.py` (`RoleSpec`, `build_agent`, the `delegate_to` tool),
`models.py` (run `Deps` + audit types), `audit.py` (append-only trail),
`team.py` (builds the five agents, the registry, the run loop, and the CLI).

Run: `python backend/team.py` (resets the DB, resolves every open ticket) or
`--ticket 101` for one.

### Audit trail (`output/audit_trail.json`)

`team.py` appends **one record per agent loop step** — it never wipes the file.
Each record has: timestamp, `run_id`, `parent_run_id` (so the delegation tree can
be rebuilt), `ticket_id`, `agent` role, `depth`, the `task` it was given, the
model, the MCP `tool_calls` (with short args/results), the `delegations` it made,
`model_requests`, its `output`, and a `stop_reason`. A smoke run on ticket #102
produced a boss → facilities → accounting chain that prepared the $2,400 rent
payment (affordable; balance would be $1,000) **without moving any cash** — cash
stayed at $3,400, ticket set to `awaiting_approval`.

---

## Safety & guardrails

Guardrails a real shop would want once agents touch real customers and real money.
Where possible they are enforced in the **tools** (the server), not just asked for
in prompts — a prompt can be ignored, a tool cannot.

**Money (enforced in the `pay` tool).**
- No agent can move money: `pay` is a reserved tool and is **filtered out of the
  agent toolset**. Agents may only *prepare* payments and POs; a human approves.
- `pay` **requires a human `approved_by`** — no approver, no payment.
- `pay` **refuses any payment that would overdraw** the account — cash can never go
  negative, and cash only ever goes out (there is no deposit tool).
- `prepare_payment` returns an `affordable` flag and the resulting balance so a
  human sees the impact and the correct payment ordering before approving.

**Vendors & customers (no real-world side effects).**
- Agents never contact real vendors; they only read the `vendors`/`invoices`
  tables and record internal POs.
- Customer replies are **drafts only** (`save_customer_message`, status `draft`);
  there is no send/email tool.
- The unpaid-invoice rule is enforced in data: `prepare_purchase_order` flags a
  `blocked_reason` when the vendor has an open invoice, so no one promises a ship
  that can't happen.

**Truth & correctness.**
- All shop facts come only from the MCP tools over the database; tools never invent
  values (empty/`None`/`error` on a miss), and prompts forbid guessing.
- "Today" is always `desk.date_today` via `get_today()`, so overdue logic is
  deterministic and testable.
- The working database is reset from the pristine copy before a full run, so runs
  are reproducible; the original DB is never written.

**Auditability.**
- Every agent step is appended to `output/audit_trail.json` (never wiped), with
  parent links, tools, and outcomes — enough to reconstruct who did what and why.
- Writes to the trail are atomic (temp-then-replace) and a corrupt file is moved
  aside, not overwritten.

**Token / cost limits (keep runs cheap and bounded).**
- Per agent run: `UsageLimits(request_limit=10)` caps model+tool calls per step.
- Delegation depth is capped (`MAX_DELEGATION_DEPTH = 4`) and a role already in the
  current chain can't be re-entered, preventing A→B→A loops.
- A whole-run budget (`Team.max_total_runs = 30`) stops a pathological fan-out.
- `reasoning_effort='none'` keeps each call lean; agents are told to use the fewest
  tool calls needed and not repeat a call.
- A 60s per-request timeout bounds a hung model call.

---

## Backend API (`backend/main.py`, FastAPI — Problem 7)

The service the React dashboard calls. Start it from the `backend/` folder:
`uvicorn main:app --reload --port 8000` → http://localhost:8000. Shop reads and the
guarded money actions go through the one MCP shop layer (`mcp_server/server.py`) —
the same code the agents use — so there is no second shop-tools layer. Approvals
call the reserved `pay` / `approve_purchase_order` tools (agents can't reach them).

Routes (one line each):

- `GET /api/health` — is the API up; returns the shop's today.
- `GET /api/tickets` — the three tickets with `status`, `resolved`, `is_open`.
- `POST /api/tickets/{id}/run` — run the agent team on that ticket; returns the boss's final decision + new status.
- `GET /api/events?limit=N` — recent agent loop steps (newest first): what each agent said, the tools it used, and its delegations (from the audit trail, so the board can refresh).
- `GET /api/approvals` — prepared payments and purchase orders still awaiting human approval.
- `POST /api/approvals/payment/{request_id}` — human approves a prepared payment; this is the only path that moves money (refuses on insufficient cash).
- `POST /api/approvals/purchase/{po_id}` — human approves a prepared purchase order (refused if the vendor is blocked by an unpaid invoice).
- `GET /api/cash` — current checking balance from `cash_accounts`.
- `POST /api/reset` — reset the working database to the original for a fresh run.
- `POST /api/tickets/{id}/resolve` — human closes a ticket once its approvals are done (refuses while any are still pending).

CORS is open to the Vite dev server (any localhost port). Approvals require a
human `approved_by`; an empty approver is rejected before any money moves. A
purchase order's block is re-checked live at approval time, so a PO prepared while
an invoice was unpaid becomes approvable once that invoice is paid.

---

## Dashboard (`frontend/`, React + Vite + TypeScript — Problem 8)

The human's window onto the team — an "operations desk". Start it from `frontend/`
with `npm run dev` and open the printed localhost URL; it talks to the backend at
`http://localhost:8000`. Three columns:

- **Ticket board** (left) — the three tickets with type icon and color-coded status
  badge (Open / Running / Awaiting approval / Blocked / Resolved); select one to get
  a **Run agent team** button.
- **Agent activity** (center) — a **live feed** (polls `/api/events` ~every 1.2s
  during a run) where each agent speaks in its own color with avatar, role, the MCP
  **tool chips** it used, and **delegation arrows**; delegations indent. After the
  run, a **summary** (boss's final decision + one card per agent) and a **Mark
  resolved** button once approvals are clear.
- **Approvals** (right) — prepared payments/POs as cards; **Approve** needs a human
  name, moves money via the backend, and a vendor-blocked PO's button is disabled
  with the reason shown.

The **checking balance** sits in the top bar and flashes when it drops after an
approved payment. Full rationale in `output/design.md`.

---

## Full resolve run (Problem 9)

Reset `data/campus_customs_new.db` to original, then ran all three tickets to
`resolved` through the dashboard, with the human approving each prepared payment.

- **Starting checking balance:** $3,400.00.
- **#101** boss → inventory → accounting: paid blocked invoice #501 ($840),
  approved a tee reprint PO → **−$840** → $2,560.
- **#102** boss → facilities → accounting: paid rent $2,400 → **−$2,400** → $160.
- **#103** boss → accounting: margin recommendation only (no discount amount
  given, no price-change tool) → **$0** → $160.
- **Ending checking balance:** **$160.00** — matches `cash_accounts` in the working
  database ($3,400 − $840 − $2,400 = $160).

Deliverables: `output/resolved_tickets.json` (per-ticket status, outcome, agent
contributions, approvals), `output/resolved_board.html` (board screenshots per
ticket), `output/desk_tickets.html` (Expected vs. Actual + the itemized Cash tab),
and the agent steps appended to `output/audit_trail.json`.

---

## Coverage map

Everything this system is made of, and where it lives:

- **Database tables** (`data/campus_customs_new.db`): `desk`, `tickets`,
  `inventory`, `vendors`, `pricing`, `invoices`, `payments`, `cash_accounts`,
  `leases`, plus agent-artifact tables `purchase_orders`, `payment_requests`,
  `customer_messages` — see **Database** above.
- **MCP tools** (`mcp_server/server.py`): 11 reads, 4 prepare/act, 2 reserved
  (`pay`, `approve_purchase_order`) — see **Full MCP tool list**.
- **Five agents** (`backend/`): boss, inventory, accounting, facilities,
  customer_service, full connectivity via `delegate_to` — see **The agent team**.
- **API routes** (`backend/main.py`): see **Backend API**.
- **Dashboard** (`frontend/`): see **Dashboard** and `output/design.md`.
- **Safety rules**: money guardrails in the `pay` tool, no real-world side effects,
  truth/never-invent, auditability, token limits — see **Safety & guardrails**.
