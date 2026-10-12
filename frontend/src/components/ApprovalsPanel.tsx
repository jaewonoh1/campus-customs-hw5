import type { Approvals } from "../types";

export default function ApprovalsPanel({
  approvals,
  approver,
  onApprover,
  onApprovePayment,
  onApprovePurchase,
  busyId,
  error,
}: {
  approvals: Approvals;
  approver: string;
  onApprover: (v: string) => void;
  onApprovePayment: (id: number) => void;
  onApprovePurchase: (id: number) => void;
  busyId: string | null;
  error: string | null;
}) {
  const nothing =
    approvals.payments.length === 0 && approvals.purchases.length === 0;

  return (
    <div className="approvals">
      <h2 className="col-title">Approvals</h2>
      <p className="approvals-note">
        Agents only <em>prepare</em> money. Nothing is paid until you approve it.
      </p>

      <label className="approver">
        Approving as
        <input
          value={approver}
          onChange={(e) => onApprover(e.target.value)}
          placeholder="your name"
        />
      </label>

      {error && <div className="approvals-error">{error}</div>}

      {nothing && <div className="approvals-empty">No pending approvals.</div>}

      {approvals.payments.map((p) => (
        <div className="approval-card" key={`pay-${p.id}`}>
          <div className="approval-top">
            <span className="approval-kind">💵 Payment · {p.kind}</span>
            <span className="approval-amount">${p.amount.toLocaleString()}</span>
          </div>
          <div className="approval-meta">
            ticket #{p.ticket_id} · {p.affordable ? "fits balance" : "⚠ over balance"}
          </div>
          <button
            className="approve-btn"
            disabled={!approver.trim() || busyId !== null}
            onClick={() => onApprovePayment(p.id)}
          >
            {busyId === `pay-${p.id}` ? "Approving…" : "✓ Approve payment"}
          </button>
        </div>
      ))}

      {approvals.purchases.map((po) => (
        <div className="approval-card" key={`po-${po.id}`}>
          <div className="approval-top">
            <span className="approval-kind">📦 Purchase · {po.sku}</span>
            <span className="approval-amount">${po.est_total.toLocaleString()}</span>
          </div>
          <div className="approval-meta">
            ticket #{po.ticket_id} · {po.qty}
            {po.size ? ` × ${po.size}` : ""} · ETA {po.eta}
          </div>
          {po.blocked_reason && (
            <div className="approval-blocked">⛔ {po.blocked_reason}</div>
          )}
          <button
            className="approve-btn"
            disabled={!approver.trim() || busyId !== null || !!po.blocked_reason}
            onClick={() => onApprovePurchase(po.id)}
          >
            {busyId === `po-${po.id}` ? "Approving…" : "✓ Approve purchase"}
          </button>
        </div>
      ))}
    </div>
  );
}
