import type { Ticket } from "../types";
import StatusBadge from "./StatusBadge";

const TYPE_META: Record<string, { icon: string; label: string }> = {
  customer_order: { icon: "🧾", label: "Customer order" },
  rent_notice: { icon: "🏠", label: "Rent notice" },
  price_override: { icon: "🏷️", label: "Price override" },
};

export default function TicketBoard({
  tickets,
  selectedId,
  runningId,
  onSelect,
  onRun,
}: {
  tickets: Ticket[];
  selectedId: number | null;
  runningId: number | null;
  onSelect: (id: number) => void;
  onRun: (id: number) => void;
}) {
  return (
    <div className="board">
      <h2 className="col-title">Ticket board</h2>
      {tickets.map((t) => {
        const meta = TYPE_META[t.type] ?? { icon: "📌", label: t.type };
        const isSelected = t.id === selectedId;
        const isRunning = t.id === runningId;
        const status = isRunning ? "running" : t.status;
        return (
          <div
            key={t.id}
            className={`ticket${isSelected ? " selected" : ""}`}
            role="button"
            tabIndex={0}
            onClick={() => onSelect(t.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") onSelect(t.id);
            }}
          >
            <div className="ticket-top">
              <span className="ticket-icon">{meta.icon}</span>
              <span className="ticket-id">#{t.id}</span>
              <StatusBadge status={status} />
            </div>
            <div className="ticket-subject">{t.subject}</div>
            <div className="ticket-meta">
              {meta.label} · {t.requester}
            </div>
            {isSelected && (
              <div
                className="ticket-actions"
                onClick={(e) => e.stopPropagation()}
              >
                <button
                  className="run-btn"
                  disabled={runningId !== null}
                  onClick={() => onRun(t.id)}
                >
                  {isRunning ? "Team at work…" : "▶ Run agent team"}
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
