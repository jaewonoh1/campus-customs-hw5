"""Campus Customs backend API.

FastAPI service the React dashboard calls. It lets a human watch the agent team
and approve the money the agents only *prepare*:

* list the tickets and whether each is open or resolved,
* run the agent team on one ticket,
* read recent agent events (what each agent said and which tools it used),
* list and approve prepared payments / purchase orders (human-in-the-loop),
* read the current checking balance,
* reset the working database to the original for a fresh run.

Shop reads and the guarded money actions go through the one MCP shop layer
(`mcp_server/server.py`) — the same code the agents use over MCP — so there is no
second shop-tools layer. Approvals call the reserved `pay` / `approve_purchase_order`
tools, which agents cannot reach.

Run from the backend/ folder:

    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import importlib.util
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import audit
from config import HW_DIR
from team import Team, reset_database

# --- the single shop layer (same module the MCP server exposes) --------------
_spec = importlib.util.spec_from_file_location("campus_shop", HW_DIR / "mcp_server" / "server.py")
shop = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(shop)

app = FastAPI(title="Campus Customs Operations API", version="1.0")

# The Vite dev server (next problem) runs on 5173/5174; allow the browser to call us.
app.add_middleware(
    CORSMiddleware,
    # The Vite dev server runs on localhost (usually :5173); allow any local port.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- request bodies ---------------------------------------------------------


class ApproveBody(BaseModel):
    approved_by: str = Field(min_length=1, description="Human who clicked approve.")


# --- routes -----------------------------------------------------------------


@app.get("/api/health")
def health() -> dict:
    """Is the API up and can it see the database?"""
    today = shop.get_today()
    return {"status": "ok", "shop_today": today.get("date_today")}


@app.get("/api/tickets")
def list_tickets() -> list[dict]:
    """The board: every ticket with its status and whether it's resolved."""
    rows = shop._query(
        "SELECT id, type, requester, subject, status, created_at FROM tickets ORDER BY id"
    )
    for r in rows:
        r["resolved"] = r["status"] == "resolved"
        r["is_open"] = r["status"] == "open"
    return rows


@app.post("/api/tickets/{ticket_id}/run")
async def run_ticket(ticket_id: int) -> dict:
    """Run the agent team on one ticket and return the boss's final decision."""
    if shop.get_ticket(ticket_id) is None:
        raise HTTPException(status_code=404, detail=f"no ticket {ticket_id}")
    decision = await Team().run_one(ticket_id)
    updated = shop.get_ticket(ticket_id) or {}
    return {"ticket_id": ticket_id, "decision": decision, "status": updated.get("status")}


@app.post("/api/tickets/{ticket_id}/resolve")
def resolve_ticket(ticket_id: int) -> dict:
    """Human closes a ticket after its prepared payments/orders are approved."""
    pend = pending_approvals()
    blocking = [
        *[p for p in pend["payments"] if p["ticket_id"] == ticket_id],
        *[p for p in pend["purchases"] if p["ticket_id"] == ticket_id],
    ]
    if blocking:
        raise HTTPException(
            status_code=409,
            detail="ticket still has pending approvals — approve them first",
        )
    updated = shop.update_ticket_status(
        ticket_id, "resolved", "Approved and closed by ops manager."
    )
    if "error" in updated:
        raise HTTPException(status_code=404, detail=updated["error"])
    return updated


@app.get("/api/events")
def recent_events(limit: int = 50) -> list[dict]:
    """Recent agent loop steps (newest first): what each agent said and its tools.

    Read from the append-only audit trail so the board can refresh.
    """
    path = audit.AUDIT_PATH
    if not path.exists():
        return []
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return []
    events = []
    for e in entries[-limit:]:
        events.append(
            {
                "timestamp": e.get("timestamp"),
                "run_id": e.get("run_id"),
                "parent_run_id": e.get("parent_run_id"),
                "ticket_id": e.get("ticket_id"),
                "agent": e.get("agent"),
                "depth": e.get("depth"),
                "said": e.get("output"),
                "tools": [c.get("tool") for c in e.get("tool_calls", [])],
                "delegations": e.get("delegations", []),
                "stop_reason": e.get("stop_reason"),
            }
        )
    events.reverse()  # newest first
    return events


@app.get("/api/approvals")
def pending_approvals() -> dict:
    """Prepared payments and purchase orders still awaiting a human's approval."""
    payments = shop._query(
        """
        SELECT id, ticket_id, kind, ref_id, amount, account, affordable, status, created_at
        FROM payment_requests WHERE status = 'pending_approval' ORDER BY id
        """
    )
    purchases = shop._query(
        """
        SELECT id, ticket_id, sku, size, qty, vendor_id, unit_cost, est_total,
               lead_days, eta, status, blocked_reason, created_at
        FROM purchase_orders WHERE status = 'pending_approval' ORDER BY id
        """
    )
    # Recompute each PO's block live: once its vendor's invoice is paid, it's no
    # longer blocked, so the dashboard can enable approval.
    for po in purchases:
        live = shop.vendor_has_open_invoice(po["vendor_id"])
        po["blocked_reason"] = (
            f"vendor {po['vendor_id']} has open unpaid invoice(s) {live['open_invoice_ids']}; "
            "pay before they will ship"
            if live["has_open_unpaid_invoice"]
            else None
        )
    return {"payments": payments, "purchases": purchases}


@app.post("/api/approvals/payment/{request_id}")
def approve_payment(request_id: int, body: ApproveBody) -> dict:
    """Human approves a prepared payment — this is the only path that moves money.

    Calls the guarded `pay` tool: it refuses if cash is insufficient (no negative
    balances) and requires a human approver.
    """
    result = shop.pay(approved_by=body.approved_by, payment_request_id=request_id)
    if not result.get("ok"):
        raise HTTPException(status_code=409, detail=result.get("error", "payment refused"))
    return result


@app.post("/api/approvals/purchase/{po_id}")
def approve_purchase(po_id: int, body: ApproveBody) -> dict:
    """Human approves a prepared purchase order (refused if vendor is blocked)."""
    result = shop.approve_purchase_order(po_id, body.approved_by)
    if not result.get("ok"):
        raise HTTPException(status_code=409, detail=result.get("error", "approval refused"))
    return result


@app.get("/api/cash")
def cash() -> dict:
    """Current checking balance from cash_accounts."""
    balance = shop.get_cash_balance("checking")
    if balance is None:
        raise HTTPException(status_code=404, detail="no checking account")
    return balance


@app.post("/api/reset")
def reset() -> dict:
    """Reset the working database to the original values for a fresh run."""
    reset_database()
    return {"ok": True, "message": "working database reset to original", "cash": shop.get_cash_balance("checking")}
