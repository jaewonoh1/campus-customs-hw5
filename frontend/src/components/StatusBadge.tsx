const LABELS: Record<string, { label: string; cls: string }> = {
  open: { label: "Open", cls: "open" },
  in_progress: { label: "In progress", cls: "progress" },
  running: { label: "Running…", cls: "running" },
  awaiting_approval: { label: "Awaiting approval", cls: "await" },
  blocked: { label: "Blocked", cls: "blocked" },
  resolved: { label: "Resolved", cls: "resolved" },
};

export default function StatusBadge({ status }: { status: string }) {
  const meta = LABELS[status] ?? { label: status, cls: "open" };
  return <span className={`badge badge-${meta.cls}`}>{meta.label}</span>;
}
