import { agentMeta } from "../agents";
import type { AgentEvent } from "../types";
import Rich from "./Rich";

export default function RunSummary({
  events,
  decision,
}: {
  events: AgentEvent[];
  decision: string | null;
}) {
  if (!decision && events.length === 0) return null;

  // One summary line per agent (its last word on this run) + the tools it used.
  const byAgent = new Map<string, { said: string; tools: Set<string> }>();
  for (const e of events) {
    const cur = byAgent.get(e.agent) ?? { said: "", tools: new Set<string>() };
    cur.said = e.said || cur.said;
    e.tools.forEach((t) => cur.tools.add(t));
    byAgent.set(e.agent, cur);
  }

  return (
    <div className="summary">
      <h3 className="summary-title">Run summary</h3>
      {decision && (
        <div className="decision">
          <div className="decision-label">Boss’s final decision</div>
          <div className="decision-text"><Rich text={decision} /></div>
        </div>
      )}
      <div className="summary-grid">
        {[...byAgent.entries()].map(([agent, info]) => {
          const m = agentMeta(agent);
          return (
            <div
              className="summary-card"
              key={agent}
              style={{ borderTopColor: m.color }}
            >
              <div className="summary-head">
                <span className="avatar small" style={{ background: m.color }}>
                  {m.initial}
                </span>
                <span style={{ color: m.color, fontWeight: 700 }}>{m.name}</span>
              </div>
              <div className="summary-said">
                {info.said ? <Rich text={info.said} /> : "—"}
              </div>
              {info.tools.size > 0 && (
                <div className="chips">
                  {[...info.tools].map((t) => (
                    <span className="chip tool" key={t}>
                      🔧 {t}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
