import type { Cash } from "../types";

export default function BalanceCard({
  cash,
  flash,
}: {
  cash: Cash | null;
  flash: boolean;
}) {
  return (
    <div className={`balance-card${flash ? " flash" : ""}`}>
      <div className="balance-label">Checking balance</div>
      <div className="balance-amount">
        {cash ? `$${cash.balance.toLocaleString()}` : "—"}
      </div>
      <div className="balance-sub">
        {cash ? `as of ${cash.date}` : "loading…"} · cash only goes out
      </div>
    </div>
  );
}
