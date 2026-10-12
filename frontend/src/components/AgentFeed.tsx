import { agentMeta } from "../agents";
import type { AgentEvent } from "../types";
import Rich from "./Rich";

export default function AgentFeed({
  events,
  running,
}: {
  events: AgentEvent[];
  running: boolean;
}) {
  if (events.length === 0) {
    return (
      <div className="feed-empty">
        {running
          ? "The team is getting started…"
          : "Pick a ticket and run the agent team to watch them work."}
      </div>
    );
  }

  return (
    <div className="feed">
      {events.map((e, i) => {
        const m = agentMeta(e.agent);
        return (
          <div
            key={`${e.run_id}-${i}`}
            className="feed-row"
            style={{ marginLeft: `${Math.min(e.depth, 3) * 22}px` }}
          >
            <div className="avatar" style={{ background: m.color }}>
              {m.initial}
            </div>
            <div
              className="bubble"
              style={{ background: m.tint, borderColor: m.color }}
            >
              <div className="bubble-head">
                <span className="bubble-name" style={{ color: m.color }}>
                  {m.name}
                </span>
                <span className="bubble-role">{m.role}</span>
              </div>
              <div className="bubble-said"><Rich text={e.said} /></div>
              {(e.tools.length > 0 || e.delegations.length > 0) && (
                <div className="chips">
                  {e.tools.map((tool, j) => (
                    <span className="chip tool" key={`t${j}`}>
                      🔧 {tool}
                    </span>
                  ))}
                  {e.delegations.map((d, j) => (
                    <span className="chip deleg" key={`d${j}`}>
                      → {agentMeta(d).name}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        );
      })}
      {running && (
        <div className="feed-row">
          <div className="avatar pulse">…</div>
          <div className="bubble working">working…</div>
        </div>
      )}
    </div>
  );
}
