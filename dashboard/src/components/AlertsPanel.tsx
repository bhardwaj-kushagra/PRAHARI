import { simClock } from "../format";
import { useSim } from "../store";
import { MechanismSwitches } from "./MechanismSwitches";
import { WhyPanel } from "./WhyPanel";

/** Alerts raised so far, each with its template explanation from the evidence trace (SPEC §4.7). Phase 6: the
 *  mechanism switches (View 5) sit above; clicking an alert opens "Why this alarm" (View 3), latest by default. */
export function AlertsPanel() {
  const source = useSim((s) => s.source);
  const simT = useSim((s) => s.simT);
  const selected = useSim((s) => s.selectedTrace);
  const selectTrace = useSim((s) => s.selectTrace);
  if (!source) return null;
  const items: { t: number; level: string; cluster: number[]; explanation: string; id: string }[] = [];
  for (let i = 0; i <= source.indexAt(simT); i++) {
    const f = source.frameAt(i);
    for (const a of f.alerts) {
      const tr = source.trace(a.trace_id);
      items.push({ t: f.t, level: a.level, cluster: a.cluster, explanation: String(tr?.explanation ?? ""), id: a.trace_id });
    }
  }
  const shown = selected && items.some((a) => a.id === selected) ? selected : items[items.length - 1]?.id ?? null;
  if (shown !== selected && shown) queueMicrotask(() => selectTrace(shown));
  return (
    <div className="alerts">
      <MechanismSwitches />
      <WhyPanel />
      <h2>Alerts so far <span className="muted small">({items.length})</span></h2>
      {items.length === 0 ? <p className="muted">No alerts yet.</p> : null}
      <ol reversed>
        {items.slice().reverse().map((a) => (
          <li key={a.id} className={a.id === shown ? "sel" : ""}>
            <button className="alert-item" onClick={() => selectTrace(a.id)} aria-pressed={a.id === shown}>
              <span className="pill pill-alert">{a.level}</span> <span className="mono">{simClock(source.header, a.t)}</span> · nodes {a.cluster.join(", ")}
            </button>
            <div className="small muted">{a.explanation}</div>
          </li>
        ))}
      </ol>
    </div>
  );
}
