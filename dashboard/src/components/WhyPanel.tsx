import { LADDER, logPos } from "../edge";
import { sci, simClock } from "../format";
import { useSim } from "../store";

interface DecisionTrace {
  trace_id: string; t: number; level: string; cluster: number[]; incident?: number; anchor?: number;
  per_node: { node: number; p_channels: number[] }[];
  scmr: { f_loc: number; f_net: number; ratio: number; pass: boolean; modelled?: boolean };
  fisher: { X: number; dof: number; p_cluster: number; method?: string };
  prior: { lambda: number; p_s: number; odds: number; day_type: string };
  bayes: { bf_bound: number; posterior_odds: number; threshold: number; quorum: number; decision: boolean; method?: string };
  explanation: string;
}

/** A horizontal log-scale bar with a threshold tick: value marker in ember when it passes, grey when it fails. */
function LogBar({ value, threshold, lo, hi, label, pass }: {
  value: number; threshold: number; lo: number; hi: number; label: string; pass: boolean;
}) {
  const x = logPos(value, lo, hi) * 100;
  const th = logPos(threshold, lo, hi) * 100;
  return (
    <div className="logbar" role="img" aria-label={`${label}: ${sci(value)} against ${sci(threshold)}, ${pass ? "pass" : "fail"}`}>
      <div className="logbar-track">
        <div className={`logbar-fill ${pass ? "pass" : "fail"}`} style={{ width: `${x}%` }} />
        <div className="logbar-threshold" style={{ left: `${th}%` }} title={`threshold ${sci(threshold)}`} />
      </div>
      <div className="logbar-scale small muted"><span>{sci(lo)}</span><span>{label}</span><span>{sci(hi)}</span></div>
    </div>
  );
}

/** SPEC §6.2 View 3 — "Why this alarm", built only from the evidence trace (§4.7). */
export function WhyPanel() {
  const source = useSim((s) => s.source);
  const id = useSim((s) => s.selectedTrace);
  if (!source || !id) return null;
  const raw = source.trace(id);
  if (!raw || raw.type !== "decision") return null;
  const tr = raw as unknown as DecisionTrace;
  const level = LADDER.indexOf(tr.level as (typeof LADDER)[number]);
  return (
    <section className="why" data-testid="why-panel" aria-label="Why this alarm">
      <h2>Why this alarm <span className="muted small">{simClock(source.header, tr.t)} · trace {tr.trace_id}
        {tr.incident !== undefined && tr.incident >= 0 ? ` · incident ${tr.incident}` : ""}</span></h2>
      <ol className="ladder" aria-label="Escalation ladder">
        {LADDER.map((lv, k) => <li key={lv} className={k === level ? "on" : k < level ? "past" : ""}>{lv}</li>)}
      </ol>
      <div className="why-grid">
        <div>
          <h3>Spatial common mode (M31)</h3>
          {tr.scmr.modelled === false ? <p className="small muted">SCMR not modelled (stub): always passes.</p> : (
            <>
              <LogBar value={tr.scmr.ratio} threshold={3} lo={0.1} hi={100} label="local ÷ network rate" pass={tr.scmr.pass} />
              <p className="small">local {(tr.scmr.f_loc * 100).toFixed(0)}% of the neighbourhood · network {(tr.scmr.f_net * 100).toFixed(0)}% ·
                ratio <b className="mono">{tr.scmr.ratio.toFixed(1)}</b> {tr.scmr.pass ? "≥" : "<"} 3</p>
            </>
          )}
        </div>
        <div>
          <h3>Combined evidence (M32)</h3>
          <table className="mini-table">
            <tbody>
              {tr.per_node.map((n) => <tr key={n.node}><td>node {n.node}</td><td className="mono">QCC p {sci(n.p_channels[0])}</td></tr>)}
            </tbody>
          </table>
          <p className="small">{tr.fisher.method === "fisher" ? "Fisher over the members' candidate p-values (r·W each)" : "Bonferroni (stub)"}:
            {" "}p<sub>C</sub>{" "}
            <b className="mono">{sci(tr.fisher.p_cluster)}</b>{tr.fisher.dof ? ` (χ² ${tr.fisher.X.toFixed(1)}, ${tr.fisher.dof} dof)` : ""}</p>
        </div>
        <div>
          <h3>Prior (M33)</h3>
          <p className="small">{tr.prior.day_type.replace("_", ", ")} day · prior odds <b className="mono">{sci(tr.prior.odds)}</b>
            {tr.prior.lambda > 0 ? <> · λ {sci(tr.prior.lambda)} × p<sub>s</sub> {tr.prior.p_s.toFixed(2)}</> : <> · legacy day-type prior</>}</p>
          <p className="small">On this prior, <b>{tr.bayes.quorum}</b> agreeing nodes are needed.</p>
        </div>
        <div>
          <h3>Decision (M34)</h3>
          <LogBar value={tr.bayes.posterior_odds} threshold={tr.bayes.threshold} lo={1e-6} hi={1e4}
                  label="posterior odds" pass={tr.bayes.posterior_odds >= tr.bayes.threshold} />
          <p className="small">BF bound {sci(tr.bayes.bf_bound)} × prior {sci(tr.prior.odds)} = <b className="mono">{sci(tr.bayes.posterior_odds)}</b>{" "}
            against {sci(tr.bayes.threshold)} · rule: {tr.bayes.method} · <b>{tr.bayes.decision ? "alarm" : "no alarm"}</b></p>
        </div>
      </div>
      <p className="why-explanation">{tr.explanation}</p>
      <p className="chart-foot">SIMULATION · built from the recorded evidence trace · seed {source.header.seed}</p>
    </section>
  );
}
