import { sci } from "../format";
import { NODE_STATE } from "../types";
import { useFrame, useSim } from "../store";

/** Minimal node readout; the full Node Inspector (View 2) arrives in Phases 2 and 5. */
export function NodePanel() {
  const source = useSim((s) => s.source);
  const i = useSim((s) => s.selectedNode);
  const frame = useFrame();
  if (!source || !frame) return null;
  if (i === null) return <p className="muted">Click a node on the map to inspect it.</p>;
  const n = source.header.nodes[i];
  const v = frame.nodes;
  const rows: [string, string][] = [
    ["State", NODE_STATE[v.state[i]]],
    ["Position", `${n.x} m, ${n.y} m`],
    ["Reading", `${v.reading[i]} su`],
    ["Residual", `${v.residual[i]} su`],
    ["p-value", sci(v.p[i])],
    ["CUSUM G / h", `${v.cusum[i]} / ${frame.cusum_h}`],
    ["Health weight", String(v.health[i])],
    ["State of charge", `${Math.round(v.soc[i] * 100)}%`],
  ];
  const L = source.header.links;
  if (L) {
    const ok = L.gateway[i] !== null;
    rows.push(["Uplink", ok ? `${L.gateway[i]} · SF${L.sf[i]}${L.modelled ? "" : " (stub: perfect link)"}` : "no link closes — needs a relay (Phase 8)"]);
    rows.push(["Distance to gateway", `${Math.round(L.d_m[i])} m`]);
    if (L.modelled) rows.push(["Path loss / received power", `${L.pl_db[i]} dB / ${L.prx_dbm[i]} dBm`]);
  }
  return (
    <div className="node-panel">
      <h2>Node {i} <span className="muted small">type {n.type}</span></h2>
      <dl className="kv">{rows.map(([k, val]) => <div key={k}><dt>{k}</dt><dd className="mono">{val}</dd></div>)}</dl>
      <p className="muted small">Values at the current frame. Time-series charts arrive with the Node Inspector.</p>
    </div>
  );
}
