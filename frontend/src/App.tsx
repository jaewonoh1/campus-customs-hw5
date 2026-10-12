import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { AgentEvent, Approvals, Cash, Ticket } from "./types";
import BalanceCard from "./components/BalanceCard";
import TicketBoard from "./components/TicketBoard";
import AgentFeed from "./components/AgentFeed";
import RunSummary from "./components/RunSummary";
import ApprovalsPanel from "./components/ApprovalsPanel";

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [cash, setCash] = useState<Cash | null>(null);
  const [cashFlash, setCashFlash] = useState(false);
  const [approvals, setApprovals] = useState<Approvals>({ payments: [], purchases: [] });

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [runningId, setRunningId] = useState<number | null>(null);
  const [runEvents, setRunEvents] = useState<AgentEvent[]>([]);
  const [decision, setDecision] = useState<string | null>(null);
  const [runFinished, setRunFinished] = useState(false);

  const [approver, setApprover] = useState("Jae");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [approveError, setApproveError] = useState<string | null>(null);
  const [banner, setBanner] = useState<string | null>(null);

  const runStartRef = useRef<string>("");
  const pollRef = useRef<number | null>(null);

  const refreshTickets = useCallback(() => api.tickets().then(setTickets).catch(() => {}), []);
  const refreshApprovals = useCallback(
    () => api.approvals().then(setApprovals).catch(() => {}),
    [],
  );
  const refreshCash = useCallback(
    (flash = false) =>
      api
        .cash()
        .then((c) => {
          setCash(c);
          if (flash) {
            setCashFlash(true);
            setTimeout(() => setCashFlash(false), 1200);
          }
        })
        .catch(() => {}),
    [],
  );

  useEffect(() => {
    refreshTickets();
    refreshCash();
    refreshApprovals();
  }, [refreshTickets, refreshCash, refreshApprovals]);

  const stopPolling = () => {
    if (pollRef.current !== null) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  // Only events from this run: for the selected ticket, after the run started.
  const pullRunEvents = useCallback(async (ticketId: number) => {
    try {
      const all = await api.events(150);
      const mine = all
        .filter((e) => e.ticket_id === ticketId && e.timestamp >= runStartRef.current)
        .sort((a, b) => a.timestamp.localeCompare(b.timestamp));
      setRunEvents(mine);
    } catch {
      /* ignore transient poll errors */
    }
  }, []);

  const runTicket = async (id: number) => {
    setRunningId(id);
    setRunFinished(false);
    setDecision(null);
    setRunEvents([]);
    setBanner(null);
    runStartRef.current = new Date().toISOString();

    // Poll the event feed while the run is in flight so the desk feels live.
    pollRef.current = window.setInterval(() => pullRunEvents(id), 1200);

    try {
      const result = await api.runTicket(id);
      setDecision(result.decision);
    } catch (err) {
      setBanner(`Run failed: ${(err as Error).message}`);
    } finally {
      stopPolling();
      await pullRunEvents(id);
      setRunningId(null);
      setRunFinished(true);
      refreshTickets();
      refreshApprovals();
      refreshCash();
    }
  };

  useEffect(() => stopPolling, []);

  const approvePayment = async (reqId: number) => {
    setBusyId(`pay-${reqId}`);
    setApproveError(null);
    try {
      await api.approvePayment(reqId, approver.trim());
      await refreshApprovals();
      await refreshCash(true);
      refreshTickets();
    } catch (err) {
      setApproveError((err as Error).message);
    } finally {
      setBusyId(null);
    }
  };

  const approvePurchase = async (poId: number) => {
    setBusyId(`po-${poId}`);
    setApproveError(null);
    try {
      await api.approvePurchase(poId, approver.trim());
      await refreshApprovals();
      refreshTickets();
    } catch (err) {
      setApproveError((err as Error).message);
    } finally {
      setBusyId(null);
    }
  };

  const resolveSelected = async (id: number) => {
    try {
      await api.resolveTicket(id);
      setBanner(`Ticket #${id} marked resolved.`);
      refreshTickets();
    } catch (err) {
      setBanner(`Can't resolve #${id}: ${(err as Error).message}`);
    }
  };

  const resetAll = async () => {
    if (runningId !== null) return;
    try {
      const res = await api.reset();
      setCash(res.cash);
      setRunEvents([]);
      setDecision(null);
      setRunFinished(false);
      setSelectedId(null);
      setBanner("Database reset to original — fresh run ready.");
      refreshTickets();
      refreshApprovals();
    } catch (err) {
      setBanner(`Reset failed: ${(err as Error).message}`);
    }
  };

  const selected = tickets.find((t) => t.id === selectedId) ?? null;

  return (
    <div className="desk">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">🐾</span>
          <div>
            <div className="brand-title">Campus Customs</div>
            <div className="brand-sub">Operations Desk · agent team on duty</div>
          </div>
        </div>
        <div className="topbar-right">
          <BalanceCard cash={cash} flash={cashFlash} />
          <button className="reset-btn" onClick={resetAll} disabled={runningId !== null}>
            ⟳ Reset shop
          </button>
        </div>
      </header>

      {banner && <div className="banner">{banner}</div>}

      <main className="grid">
        <aside className="col left">
          <TicketBoard
            tickets={tickets}
            selectedId={selectedId}
            runningId={runningId}
            onSelect={setSelectedId}
            onRun={runTicket}
          />
        </aside>

        <section className="col center">
          <div className="center-head">
            <h2 className="col-title">
              {selected ? `Ticket #${selected.id} · ${selected.subject}` : "Agent activity"}
            </h2>
            {runningId !== null && <span className="live-dot">● live</span>}
            {runFinished && runningId === null && (
              <span className="done-dot">✓ run complete</span>
            )}
            {selected &&
              runningId === null &&
              selected.status === "awaiting_approval" && (
                <button
                  className="resolve-btn"
                  onClick={() => resolveSelected(selected.id)}
                >
                  ✓ Mark resolved
                </button>
              )}
          </div>
          <AgentFeed events={runEvents} running={runningId !== null} />
          {runFinished && runningId === null && (
            <RunSummary events={runEvents} decision={decision} />
          )}
        </section>

        <aside className="col right">
          <ApprovalsPanel
            approvals={approvals}
            approver={approver}
            onApprover={setApprover}
            onApprovePayment={approvePayment}
            onApprovePurchase={approvePurchase}
            busyId={busyId}
            error={approveError}
          />
        </aside>
      </main>
    </div>
  );
}
