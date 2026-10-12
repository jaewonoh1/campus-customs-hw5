// Shapes returned by the backend API (Problem 7).

export interface Ticket {
  id: number;
  type: string;
  requester: string;
  subject: string;
  status: string;
  created_at: string;
  resolved: boolean;
  is_open: boolean;
}

export interface AgentEvent {
  timestamp: string;
  run_id: string;
  parent_run_id: string | null;
  ticket_id: number | null;
  agent: string;
  depth: number;
  said: string;
  tools: string[];
  delegations: string[];
  stop_reason: string;
}

export interface Cash {
  name: string;
  balance: number;
  date: string;
}

export interface PaymentRequest {
  id: number;
  ticket_id: number | null;
  kind: string;
  ref_id: number | null;
  amount: number;
  account: string;
  affordable: number;
  status: string;
  created_at: string;
}

export interface PurchaseOrder {
  id: number;
  ticket_id: number | null;
  sku: string;
  size: string | null;
  qty: number;
  vendor_id: number;
  unit_cost: number;
  est_total: number;
  lead_days: number;
  eta: string;
  status: string;
  blocked_reason: string | null;
  created_at: string;
}

export interface Approvals {
  payments: PaymentRequest[];
  purchases: PurchaseOrder[];
}

export interface RunResult {
  ticket_id: number;
  decision: string;
  status: string;
}
