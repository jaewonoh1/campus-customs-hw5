"""Campus Customs MCP server.

A FastMCP server that exposes the shop's database to the agent team. Every agent
in this homework calls tools defined here — it is the single, auditable surface
for reading and changing shop state. There is no second shop-tools layer; all
shop facts come from this server over `data/campus_customs_new.db`.

Tools fall into three groups:

* reads — return rows exactly as stored; never invent data (a miss returns an
  empty list / `None` / an `{"error": ...}` dict, never a made-up value).
* prepare/act — agents use these to work tickets: update a ticket's status, and
  prepare purchase orders / payments / customer messages that a human approves
  later. Prepared artifacts are persisted so the dashboard can show them.
* reserved — `pay` actually moves money. It is NOT given to the agents; it is for
  the human-approval step (the dashboard, a later problem). It enforces the money
  guardrails: every payment needs a human approver and cash can never go negative.

Run:  python mcp_server/server.py        (stdio transport)
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

# The working copy of the database (the full resolve run resets this to the
# original before starting). The original `campus_customs.db` is never touched.
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs_new.db"

mcp = FastMCP("campus-customs")


# --- database helpers ------------------------------------------------------


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure_artifact_tables(conn)
    return conn


def _query(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def _one(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    rows = _query(sql, params)
    return rows[0] if rows else None


def _ensure_artifact_tables(conn: sqlite3.Connection) -> None:
    """Create the tables that hold agent-prepared artifacts awaiting a human.

    These hold work the agents *prepare* (not shop facts): purchase orders,
    payment requests, and customer message drafts. They live in the working copy
    and are recreated on demand, so resetting the database simply clears them.
    """
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS purchase_orders (
            id INTEGER PRIMARY KEY,
            ticket_id INTEGER,
            sku TEXT NOT NULL,
            size TEXT,
            qty INTEGER NOT NULL,
            vendor_id INTEGER NOT NULL,
            unit_cost REAL NOT NULL,
            est_total REAL NOT NULL,
            lead_days INTEGER NOT NULL,
            eta TEXT NOT NULL,
            status TEXT NOT NULL,          -- pending_approval | approved | rejected
            blocked_reason TEXT,
            prepared_by TEXT,
            created_at TEXT NOT NULL,
            approved_by TEXT,
            approved_at TEXT
        );
        CREATE TABLE IF NOT EXISTS payment_requests (
            id INTEGER PRIMARY KEY,
            ticket_id INTEGER,
            kind TEXT NOT NULL,            -- invoice | rent | other
            ref_id INTEGER,
            amount REAL NOT NULL,
            account TEXT NOT NULL,
            affordable INTEGER NOT NULL,   -- 1/0: fits current balance
            status TEXT NOT NULL,          -- pending_approval | approved | paid | rejected
            prepared_by TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS customer_messages (
            id INTEGER PRIMARY KEY,
            ticket_id INTEGER,
            recipient TEXT NOT NULL,
            body TEXT NOT NULL,
            status TEXT NOT NULL,          -- draft (never 'sent'; we do not email)
            drafted_by TEXT,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def _today(conn: sqlite3.Connection | None = None) -> str:
    """The shop's 'today' — desk.date_today, never the real clock."""
    own = conn is None
    conn = conn or _connect()
    try:
        row = conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
        return row[0] if row else ""
    finally:
        if own:
            conn.close()


# --- reads -----------------------------------------------------------------


@mcp.tool
def get_today() -> dict[str, Any]:
    """The shop's current date and desk notes.

    `date_today` is the shop's 'today' — use it (not the real calendar) to decide
    what is overdue or due soon.
    """
    return _one("SELECT date_today, notes FROM desk LIMIT 1") or {"date_today": "", "notes": None}


@mcp.tool
def list_open_tickets() -> list[dict[str, Any]]:
    """List every open ticket on the board, newest first.

    The work board the boss routes from. Each ticket includes its linking fields
    (`sku`, `size`, `qty`, `lease_id`, `invoice_id`) so an agent can follow it
    into inventory, pricing, leases, or invoices. Empty list if none are open.
    """
    return _query(
        """
        SELECT id, type, requester, subject, sku, size, qty,
               lease_id, invoice_id, status, notes, created_at
        FROM tickets WHERE status = 'open' ORDER BY created_at DESC
        """
    )


@mcp.tool
def get_ticket(ticket_id: int) -> dict[str, Any] | None:
    """Get one ticket by id (any status). `None` if there is no such ticket."""
    return _one(
        """
        SELECT id, type, requester, subject, sku, size, qty,
               lease_id, invoice_id, status, notes, created_at
        FROM tickets WHERE id = ?
        """,
        (ticket_id,),
    )


@mcp.tool
def check_stock(sku: str, size: str | None = None) -> list[dict[str, Any]]:
    """Check on-hand stock for a product, optionally for one size.

    Used by inventory to read current quantities and spot shortfalls (a `qty` of
    0, or below a ticket's requested qty). Pass just `sku` for all sizes, or
    `sku`+`size` for one row. Empty list if the SKU (or SKU+size) isn't stocked.
    """
    if size is None:
        return _query(
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? ORDER BY size",
            (sku,),
        )
    return _query(
        "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ?",
        (sku, size),
    )


@mcp.tool
def get_pricing(sku: str) -> dict[str, Any] | None:
    """Unit cost and list price for a product, with the derived margin.

    Used by accounting to check margins and vet price-override / bulk-discount
    requests. `margin` and `margin_pct` are computed from the stored `unit_cost`
    and `list_price`. `None` if the SKU has no pricing row.
    """
    row = _one("SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?", (sku,))
    if row is None:
        return None
    row["margin"] = round(row["list_price"] - row["unit_cost"], 2)
    row["margin_pct"] = (
        round((row["list_price"] - row["unit_cost"]) / row["list_price"] * 100, 1)
        if row["list_price"]
        else None
    )
    return row


@mcp.tool
def list_vendors() -> list[dict[str, Any]]:
    """All vendors with their specialty and lead time.

    Used by inventory to pick which vendor can restock a SKU. `lead_days` is the
    authoritative restock lead time; `specialty` says what each vendor supplies.
    """
    return _query("SELECT id, name, specialty, lead_days FROM vendors ORDER BY id")


@mcp.tool
def list_invoices(status: str | None = None) -> list[dict[str, Any]]:
    """Vendor invoices, optionally filtered by status (e.g. 'open').

    Used by accounting to see what the shop owes. An `open` invoice is unpaid.
    """
    if status is None:
        return _query(
            "SELECT id, vendor_id, amount, due_date, status, description FROM invoices ORDER BY id"
        )
    return _query(
        "SELECT id, vendor_id, amount, due_date, status, description FROM invoices WHERE status = ? ORDER BY id",
        (status,),
    )


@mcp.tool
def vendor_has_open_invoice(vendor_id: int) -> dict[str, Any]:
    """Whether a vendor has an open (unpaid) invoice — they won't ship if so.

    Inventory/accounting must check this before promising a restock: a vendor
    will not ship new product while it has an open unpaid invoice.
    """
    open_invoices = _query(
        "SELECT id, amount, due_date FROM invoices WHERE vendor_id = ? AND status = 'open'",
        (vendor_id,),
    )
    return {
        "vendor_id": vendor_id,
        "has_open_unpaid_invoice": len(open_invoices) > 0,
        "open_invoice_ids": [i["id"] for i in open_invoices],
        "open_invoice_total": round(sum(i["amount"] for i in open_invoices), 2),
    }


@mcp.tool
def get_cash_balance(account: str = "checking") -> dict[str, Any] | None:
    """Current cash balance for an account. `None` if the account doesn't exist.

    The money guardrail reads from here: a payment can never take a balance
    negative, and cash only ever goes out.
    """
    return _one("SELECT name, balance, date FROM cash_accounts WHERE name = ?", (account,))


@mcp.tool
def list_leases() -> list[dict[str, Any]]:
    """All shop leases: space, landlord, monthly rent, and next due date.

    The facilities agent's data for rent/space decisions, judged against
    `get_today()`.
    """
    return _query(
        "SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases ORDER BY id"
    )


@mcp.tool
def get_lease(lease_id: int) -> dict[str, Any] | None:
    """Get one lease by id. `None` if there is no such lease."""
    return _one(
        "SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases WHERE id = ?",
        (lease_id,),
    )


# --- prepare / act (agent-callable; change the working copy) ----------------


@mcp.tool
def update_ticket_status(ticket_id: int, status: str, note: str = "") -> dict[str, Any]:
    """Set a ticket's status and optionally append a note.

    Used to move a ticket forward (e.g. 'in_progress', 'resolved',
    'blocked', 'awaiting_approval'). Returns the updated ticket, or an
    `{"error": ...}` dict if the ticket doesn't exist.
    """
    conn = _connect()
    try:
        row = conn.execute("SELECT notes FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row is None:
            return {"error": f"no ticket {ticket_id}"}
        notes = row["notes"] or ""
        if note:
            stamp = _today(conn)
            notes = f"{notes}\n[{stamp}] {note}".strip()
        conn.execute(
            "UPDATE tickets SET status = ?, notes = ? WHERE id = ?",
            (status, notes, ticket_id),
        )
        conn.commit()
    finally:
        conn.close()
    return get_ticket(ticket_id) or {"error": f"no ticket {ticket_id}"}


@mcp.tool
def prepare_purchase_order(
    ticket_id: int | None,
    sku: str,
    qty: int,
    vendor_id: int,
    size: str | None = None,
    prepared_by: str = "accounting",
) -> dict[str, Any]:
    """Prepare a purchase order for a restock, pending human approval.

    Does NOT order or ship anything — it records a PO a human can approve later.
    Cost comes from `pricing`, lead time and specialty from `vendors`; the ETA is
    `get_today()` + the vendor's `lead_days`. If the vendor has an open unpaid
    invoice (so they won't ship), the PO is still recorded but flagged with a
    `blocked_reason`. Returns `{"error": ...}` if the SKU or vendor is unknown.
    """
    pricing = _one("SELECT unit_cost FROM pricing WHERE sku = ?", (sku,))
    if pricing is None:
        return {"error": f"no pricing for sku {sku}"}
    vendor = _one("SELECT id, name, specialty, lead_days FROM vendors WHERE id = ?", (vendor_id,))
    if vendor is None:
        return {"error": f"no vendor {vendor_id}"}

    unit_cost = pricing["unit_cost"]
    est_total = round(unit_cost * qty, 2)
    today = _today()
    eta = (date.fromisoformat(today) + timedelta(days=vendor["lead_days"])).isoformat()
    block = vendor_has_open_invoice(vendor_id)
    blocked_reason = (
        f"vendor {vendor_id} has open unpaid invoice(s) {block['open_invoice_ids']}; "
        "pay before they will ship"
        if block["has_open_unpaid_invoice"]
        else None
    )
    created_at = today
    conn = _connect()
    try:
        cur = conn.execute(
            """
            INSERT INTO purchase_orders
              (ticket_id, sku, size, qty, vendor_id, unit_cost, est_total,
               lead_days, eta, status, blocked_reason, prepared_by, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                ticket_id, sku, size, qty, vendor_id, unit_cost, est_total,
                vendor["lead_days"], eta, "pending_approval", blocked_reason,
                prepared_by, created_at,
            ),
        )
        conn.commit()
        po_id = cur.lastrowid
    finally:
        conn.close()
    return {
        "id": po_id,
        "ticket_id": ticket_id,
        "sku": sku,
        "size": size,
        "qty": qty,
        "vendor_id": vendor_id,
        "vendor_name": vendor["name"],
        "unit_cost": unit_cost,
        "est_total": est_total,
        "lead_days": vendor["lead_days"],
        "eta": eta,
        "status": "pending_approval",
        "blocked_reason": blocked_reason,
    }


@mcp.tool
def prepare_payment(
    ticket_id: int | None,
    kind: str,
    amount: float,
    ref_id: int | None = None,
    account: str = "checking",
    prepared_by: str = "accounting",
) -> dict[str, Any]:
    """Prepare a payment for human approval — does NOT move any money.

    `kind` is 'invoice', 'rent', or 'other'; `ref_id` links it (invoice id or
    lease id). The request is recorded as `pending_approval` with an `affordable`
    flag (does it fit the current balance?) and the balance it would leave.
    Paying actually happens only via the reserved `pay` tool, after a human
    approves. Returns `{"error": ...}` if the account is unknown.
    """
    cash = get_cash_balance(account)
    if cash is None:
        return {"error": f"no account '{account}'"}
    balance = cash["balance"]
    affordable = amount <= balance
    today = _today()
    conn = _connect()
    try:
        cur = conn.execute(
            """
            INSERT INTO payment_requests
              (ticket_id, kind, ref_id, amount, account, affordable, status, prepared_by, created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (ticket_id, kind, ref_id, amount, account, int(affordable),
             "pending_approval", prepared_by, today),
        )
        conn.commit()
        req_id = cur.lastrowid
    finally:
        conn.close()
    return {
        "id": req_id,
        "ticket_id": ticket_id,
        "kind": kind,
        "ref_id": ref_id,
        "amount": amount,
        "account": account,
        "current_balance": balance,
        "affordable": affordable,
        "balance_after_if_paid": round(balance - amount, 2),
        "status": "pending_approval",
        "note": "Awaiting human approval. Not paid. Cash cannot go negative.",
    }


@mcp.tool
def save_customer_message(
    ticket_id: int | None,
    body: str,
    recipient: str = "customer",
    drafted_by: str = "customer_service",
) -> dict[str, Any]:
    """Save a DRAFT customer message. It is never sent — we do not email anyone.

    Customer service uses this to draft replies a human can review and send.
    Returns the saved draft record.
    """
    today = _today()
    conn = _connect()
    try:
        cur = conn.execute(
            """
            INSERT INTO customer_messages
              (ticket_id, recipient, body, status, drafted_by, created_at)
            VALUES (?,?,?,?,?,?)
            """,
            (ticket_id, recipient, body, "draft", drafted_by, today),
        )
        conn.commit()
        msg_id = cur.lastrowid
    finally:
        conn.close()
    return {
        "id": msg_id,
        "ticket_id": ticket_id,
        "recipient": recipient,
        "body": body,
        "status": "draft",
        "note": "Draft only — not emailed.",
    }


# --- reserved: human-approval money tool (NOT given to the agents) -----------


@mcp.tool
def pay(
    approved_by: str,
    payment_request_id: int | None = None,
    kind: str | None = None,
    ref_id: int | None = None,
    amount: float | None = None,
    account: str = "checking",
) -> dict[str, Any]:
    """Execute a payment. Reserved for the human-approval step — NOT for agents.

    Guardrails enforced here, not just in prompts:
    * `approved_by` (a human) is required — no approval, no payment.
    * the payment is REFUSED if it would overdraw the account (cash never goes
      negative); cash only ever goes out.
    Pass a `payment_request_id` (preferred) to pay a prepared request, or
    `kind`/`ref_id`/`amount` directly. On success it debits cash, appends to
    `payments`, marks a paid invoice as 'paid', and closes the request.
    """
    if not approved_by or not approved_by.strip():
        return {"ok": False, "error": "human approval required: approved_by is empty"}

    conn = _connect()
    try:
        if payment_request_id is not None:
            req = conn.execute(
                "SELECT * FROM payment_requests WHERE id = ?", (payment_request_id,)
            ).fetchone()
            if req is None:
                return {"ok": False, "error": f"no payment request {payment_request_id}"}
            if req["status"] == "paid":
                return {"ok": False, "error": f"payment request {payment_request_id} already paid"}
            kind, ref_id, amount, account = req["kind"], req["ref_id"], req["amount"], req["account"]
        if amount is None:
            return {"ok": False, "error": "nothing to pay: provide payment_request_id or amount"}

        cash = conn.execute(
            "SELECT balance FROM cash_accounts WHERE name = ?", (account,)
        ).fetchone()
        if cash is None:
            return {"ok": False, "error": f"no account '{account}'"}
        balance = cash["balance"]
        if amount > balance:
            return {
                "ok": False,
                "error": "insufficient cash: refusing payment (no negative balances)",
                "balance": balance,
                "amount": amount,
            }

        today = _today(conn)
        new_balance = round(balance - amount, 2)
        conn.execute(
            "UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?",
            (new_balance, today, account),
        )
        conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?,?,?,?,?,?)",
            (kind, ref_id, amount, account, today, approved_by),
        )
        if kind == "invoice" and ref_id is not None:
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (ref_id,))
        if payment_request_id is not None:
            conn.execute(
                "UPDATE payment_requests SET status = 'paid' WHERE id = ?",
                (payment_request_id,),
            )
        conn.commit()
    finally:
        conn.close()
    return {
        "ok": True,
        "kind": kind,
        "ref_id": ref_id,
        "amount": amount,
        "account": account,
        "new_balance": new_balance,
        "approved_by": approved_by,
        "paid_at": today,
    }


@mcp.tool
def approve_purchase_order(po_id: int, approved_by: str) -> dict[str, Any]:
    """Approve a prepared purchase order. Reserved for the human-approval step.

    Requires a human `approved_by`. A PO blocked by an open unpaid invoice cannot
    be approved until that invoice is paid. Marks the PO 'approved' and stamps who
    approved it and when.
    """
    if not approved_by or not approved_by.strip():
        return {"ok": False, "error": "human approval required: approved_by is empty"}
    conn = _connect()
    try:
        po = conn.execute("SELECT * FROM purchase_orders WHERE id = ?", (po_id,)).fetchone()
        if po is None:
            return {"ok": False, "error": f"no purchase order {po_id}"}
        if po["status"] == "approved":
            return {"ok": False, "error": f"purchase order {po_id} already approved"}
        # Re-check the vendor block live: a PO prepared while an invoice was unpaid
        # becomes approvable once that invoice is actually paid.
        live_block = vendor_has_open_invoice(po["vendor_id"])
        if live_block["has_open_unpaid_invoice"]:
            return {
                "ok": False,
                "error": (
                    f"cannot approve: vendor {po['vendor_id']} still has open unpaid "
                    f"invoice(s) {live_block['open_invoice_ids']} — pay before they ship"
                ),
            }
        conn.execute(
            "UPDATE purchase_orders SET status = 'approved', approved_by = ?, approved_at = ? WHERE id = ?",
            (approved_by, _today(conn), po_id),
        )
        conn.commit()
    finally:
        conn.close()
    return {"ok": True, "po_id": po_id, "status": "approved", "approved_by": approved_by}


if __name__ == "__main__":
    mcp.run(show_banner=False)
