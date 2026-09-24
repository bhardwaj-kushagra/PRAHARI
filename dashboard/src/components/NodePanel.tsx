import { MODE_NAME } from "../comms";
import { sci } from "../format";
import { NODE_STATE } from "../types";
import { useFrame, useSim } from "../store";

/** Node readout and badges (SPEC §6.2 View 2); the stacked evidence charts are in NodeInspector (Phase 5). */
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
    ...(v.n_cal ? [["Calibration n / floor p_min", `${v.n_cal[i]} / ${sci(1 / (v.n_cal[i] + 1))}`] as [string, string]] : []),
    ["Health weight (M29)", v.health[i] < 0.1 ? `${v.health[i]} — this sensor abstains` : String(v.health[i])],
    ["State of charge", `${Math.round(v.soc[i] * 100)}%`],
    ...(v.mode ? [["Power mode (M43)", MODE_NAME[v.mode[i]]] as [string, string]] : []),
    ...(v.queue ? [["Frames waiting (store-and-forward)", String(v.queue[i])] as [string, string]] : []),
  ];
  const L = source.header.links;
  if (L) {
    const ok = L.gateway[i] !== null;
    const relay = L.relay?.[i];
    rows.push(["Uplink", ok ? `${L.gateway[i]} · SF${L.sf[i]}${L.modelled ? "" : " (stub: perfect link)"}`
                            : relay !== null && relay !== undefined ? `via relay node ${relay} (TS011)` : "no link closes — needs a relay"]);
    rows.push(["Distance to gateway", `${Math.round(L.d_m[i])} m`]);
    if (L.modelled) rows.push(["Path loss / received power", `${L.pl_db[i]} dB / ${L.prx_dbm[i]} dBm`]);
  }
  return (
    <div className="node-panel">
      <h2>Node {i} <span className="muted small">type {n.type}</span></h2>
      <dl className="kv">{rows.map(([k, val]) => <div key={k}><dt>{k}</dt><dd className="mono">{val}</dd></div>)}</dl>
      <p className="muted small">Values at the current frame; the charts below cover the whole recording.</p>
    </div>
  );
}
