import { simClock } from "../format";
import { useSim } from "../store";

/** Alerts raised so far, each with its template explanation from the evidence trace (SPEC §4.7). */
export function AlertsPanel() {
  const source = useSim((s) => s.source);
  const simT = useSim((s) => s.simT);
  if (!source) return null;
  const items: { t: number; level: string; cluster: number[]; explanation: string }[] = [];
  for (let i = 0; i <= source.indexAt(simT); i++) {
    const f = source.frameAt(i);
    for (const a of f.alerts) {
      const tr = source.trace(a.trace_id);
      items.push({ t: f.t, level: a.level, cluster: a.cluster, explanation: String(tr?.explanation ?? "") });
    }
  }
  return (
    <div className="alerts">
      <h2>Alerts so far <span className="muted small">({items.length})</span></h2>
      {items.length === 0 ? <p className="muted">No alerts yet.</p> : null}
      <ol reversed>
        {items.slice().reverse().map((a, k) => (
          <li key={k}>
            <div><span className="pill pill-alert">{a.level}</span> <span className="mono">{simClock(source.header, a.t)}</span> · nodes {a.cluster.join(", ")}{" "}</div>
            <div className="small muted">{a.explanation}</div>
          </li>
        ))}
      </ol>
    </div>
  );
}
