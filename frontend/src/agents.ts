// Per-agent identity: color, initial, and a one-line role, so each agent reads
// distinctly in the activity feed and the summary.

export interface AgentMeta {
  key: string;
  name: string;
  initial: string;
  role: string;
  color: string;   // accent (text / border)
  tint: string;    // soft background for that agent's cards
}

export const AGENTS: Record<string, AgentMeta> = {
  boss: {
    key: "boss",
    name: "Boss",
    initial: "B",
    role: "Routes the ticket, makes the final call",
    color: "#6a3d9a",
    tint: "#f3eefb",
  },
  inventory: {
    key: "inventory",
    name: "Inventory",
    initial: "I",
    role: "Stock, shortfalls, which vendor can restock",
    color: "#0b7a3b",
    tint: "#e9f6ee",
  },
  accounting: {
    key: "accounting",
    name: "Accounting",
    initial: "A",
    role: "Cash, invoices, margins, prepares payments",
    color: "#00356b",
    tint: "#eaf1fa",
  },
  facilities: {
    key: "facilities",
    name: "Facilities",
    initial: "F",
    role: "Lease, rent, the shop space",
    color: "#b25e00",
    tint: "#fbf0e3",
  },
  customer_service: {
    key: "customer_service",
    name: "Customer Service",
    initial: "C",
    role: "Drafts messages for customers",
    color: "#b02a5b",
    tint: "#fbeaf1",
  },
};

export function agentMeta(key: string): AgentMeta {
  return (
    AGENTS[key] ?? {
      key,
      name: key,
      initial: key.slice(0, 1).toUpperCase(),
      role: "",
      color: "#5b6672",
      tint: "#eef1f6",
    }
  );
}
