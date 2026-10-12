// Thin typed client for the Campus Customs backend.
// The dashboard talks to the FastAPI backend directly; override with VITE_API_BASE.

import type {
  Approvals,
  Cash,
  RunResult,
  AgentEvent,
  Ticket,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const data = await res.json();
      if (data?.detail) detail = data.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  tickets: () => get<Ticket[]>("/api/tickets"),
  cash: () => get<Cash>("/api/cash"),
  events: (limit = 100) => get<AgentEvent[]>(`/api/events?limit=${limit}`),
  approvals: () => get<Approvals>("/api/approvals"),
  runTicket: (id: number) => post<RunResult>(`/api/tickets/${id}/run`),
  resolveTicket: (id: number) => post(`/api/tickets/${id}/resolve`),
  approvePayment: (id: number, approved_by: string) =>
    post(`/api/approvals/payment/${id}`, { approved_by }),
  approvePurchase: (id: number, approved_by: string) =>
    post(`/api/approvals/purchase/${id}`, { approved_by }),
  reset: () => post<{ ok: boolean; cash: Cash }>("/api/reset"),
};
