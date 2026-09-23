import { glowOpacity, glyphScale, latestPlume, recentBaselineAlarms } from "../layers";
import { useMapView } from "../mapView";
import type { FireState, Header } from "../types";
import { NODE_STATE } from "../types";
import { useFrame, useSim } from "../store";
import { hasPhase8 } from "../comms";
import { PacketLayer, SocLayer } from "./CommsLayers";
import { CoverageLayer, InterfaceLayer, LikelihoodLayer, LinksLayer, PlumeLayer, PreviewNodes, SatelliteLayer } from "./MapLayers";

const GLYPH_R = 7;

/** One node glyph; shape as well as colour encodes the state (SPEC §6.3). */
function NodeGlyph({ state, selected }: { state: number; selected: boolean }) {
  const ring = selected ? <circle r={GLYPH_R + 5} className="glyph-select" /> : null;
  switch (state) {
    case 1: return <g>{ring}<circle r={GLYPH_R - 1} className="glyph-elevated" /></g>;
    case 2: return <g>{ring}<circle r={GLYPH_R + 3} className="glyph-pulse" /><circle r={GLYPH_R - 2} className="glyph-ember" /></g>;
    case 3: return <g>{ring}<circle r={GLYPH_R + 5} className="glyph-halo" /><circle r={GLYPH_R - 1} className="glyph-ember" /></g>;
    case 4: return <g>{ring}<path d="M-5,-5L5,5M5,-5L-5,5" className="glyph-fault" /></g>;
    case 5: return <g>{ring}<circle r={GLYPH_R - 2} className="glyph-lowpower" /></g>;
    default: return <g>{ring}<circle r={GLYPH_R - 3} className="glyph-normal" /></g>;
  }
}

function Fire({ f, H, k, windTo }: { f: FireState; H: number; k: number; windTo: number }) {
  const r = Math.max(6 * k, Math.sqrt(f.area_m2 / Math.PI));
  const dx = Math.sin(windTo) * 28 * k;
  const dy = -Math.cos(windTo) * 28 * k;           // local wind arrow: the plume drifts this way (M12/M16)
  return (
    <g transform={`translate(${f.x},${H - f.y})`} className="fire">
      <title>fire {f.id} · {Math.round(f.age_min)} min · {Math.round(f.area_m2)} m² (SIM)</title>
      <circle r={r} className="fire-perimeter" />
      <line x1={r * Math.sin(windTo)} y1={-r * Math.cos(windTo)} x2={r * Math.sin(windTo) + dx} y2={-r * Math.cos(windTo) + dy}
            className="fire-wind" strokeWidth={2 * k} markerEnd="url(#arrow)" />
      <path d="M0,-9L7,0L0,9L-7,0Z" className="fire-core" transform={`scale(${k})`} />
      <text y={-r - 6 * k} className="map-label" textAnchor="middle" style={{ fontSize: 13 * k }}>F{f.id}</text>
    </g>
  );
}

function WindArrow({ speed, fromDeg, header, k }: { speed: number; fromDeg: number; header: Header; k: number }) {
  const to = ((fromDeg + 180) % 360) * (Math.PI / 180);
  const len = 36;
  const dx = Math.sin(to) * len;
  const dy = -Math.cos(to) * len;             // SVG y points down; north is up
  const x0 = header.map.width_m / k + 85;      // in the right-hand margin, clear of the network
  const y0 = 60;
  return (
    <g className="wind" aria-label={`wind ${speed} m/s from ${fromDeg} degrees`} transform={`scale(${k})`}>
      <circle cx={x0} cy={y0} r={44} className="wind-dial" />
      <line x1={x0 - dx / 2} y1={y0 - dy / 2} x2={x0 + dx / 2} y2={y0 + dy / 2} className="wind-line" markerEnd="url(#arrow)" />
      <text x={x0} y={y0 + 62} textAnchor="middle" className="map-label">wind {speed} m/s</text>
      <text x={x0} y={y0 + 80} textAnchor="middle" className="map-label">from {fromDeg}°</text>
    </g>
  );
}

/** P0 alarms (grey triangle above the node) and P1 alarms (dashed grey ring on each member) from the last 30 min. */
function BaselineMarks({ h, H, k, t }: { h: Header; H: number; k: number; t: number }) {
  const source = useSim((s) => s.source);
  if (!source) return null;
  const { p0, p1 } = recentBaselineAlarms(source, t, 30);
  return (
    <g className="baselines" aria-label="baseline alarms">
      {[...p1].map((i) => <circle key={`p1-${i}`} cx={h.nodes[i].x} cy={H - h.nodes[i].y} r={15 * k} className="p1-mark"
                                  strokeWidth={1.8 * k}><title>P1 alarm (v1) · node {i} · SIM</title></circle>)}
      {[...p0].map((i) => (
        <path key={`p0-${i}`} transform={`translate(${h.nodes[i].x},${H - h.nodes[i].y - 13 * k}) scale(${k})`}
              d="M0,-5L5,4L-5,4Z" className="p0-mark"><title>P0 alarm (fixed threshold) · node {i} · SIM</title></path>
      ))}
    </g>
  );
}

export function CommandMap() {
  const source = useSim((s) => s.source);
  const selected = useSim((s) => s.selectedNode);
  const selectNode = useSim((s) => s.selectNode);
  const layers = useMapView((s) => s.layers);
  const preview = useMapView((s) => s.preview);
  const frame = useFrame();
  if (!source || !frame) return <div className="map-empty">Open a recording to see the network.</div>;
  const h = source.header;
  const W = h.map.width_m;
  const H = h.map.height_m;
  const k = glyphScale(W);
  const active = h.layouts?.active ?? "grid";
  const p8 = hasPhase8(frame);
  const previewing = preview !== null && preview !== active && !!h.layouts?.[preview];
  const shownNodes: [number, number][] = previewing
    ? (h.layouts?.[preview!]?.nodes ?? [])
    : h.nodes.map((n) => [n.x, n.y]);
  return (
    <figure className="map">
      <svg viewBox={`${-20 * k} ${-20 * k} ${W + 190 * k} ${H + 40 * k}`} role="img"
           aria-label="Command map of the simulated forest and sensor network">
        <defs>
          <pattern id="forest" width="28" height="28" patternUnits="userSpaceOnUse">
            <circle cx="7" cy="7" r="2.2" className="tree" />
            <circle cx="21" cy="19" r="1.6" className="tree" />
          </pattern>
          <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
            <path d="M0,0L10,5L0,10z" className="wind-head" />
          </marker>
        </defs>
        <rect x={0} y={0} width={W} height={H} className="forest" />
        <rect x={0} y={0} width={W} height={H} fill="url(#forest)" />
        {layers.likelihood ? <LikelihoodLayer h={h} H={H} /> : null}
        {layers.interfaces ? <InterfaceLayer h={h} H={H} /> : null}
        {layers.satellite ? <SatelliteLayer h={h} H={H} /> : null}
        {layers.coverage ? <CoverageLayer h={h} H={H} nodes={shownNodes} /> : null}
        {layers.links && !previewing ? <LinksLayer h={h} H={H} /> : null}
        {layers.packets && !previewing && p8.comms ? <PacketLayer h={h} H={H} source={source} frame={frame} /> : null}
        {layers.energy && !previewing && p8.energy ? <SocLayer h={h} H={H} frame={frame} /> : null}
        {h.gateways.map((g) => {
          const down = frame.gateways_down?.includes(g.id) ?? false;
          return (
            <g key={g.id} transform={`translate(${g.x},${H - g.y}) scale(${k})`} className={down ? "gw-down" : undefined}>
              <rect x={-8} y={-8} width={16} height={16} className="gateway" />
              {down ? <path d="M-11,-11L11,11M11,-11L-11,11" className="gw-cross" /> : null}
              <text y={-14} textAnchor="middle" className="map-label">{down ? `${g.id} · out of service` : g.id}</text>
              {down ? <title>{`${g.id} out of service: nodes hold candidate frames (store-and-forward) · SIM`}</title> : null}
            </g>
          );
        })}
        {layers.smoke ? <PlumeLayer frame={latestPlume(source, frame.t, 3 * h.record_every * h.tick_minutes)} H={H} /> : null}
        {frame.fires.map((f) => <Fire key={f.id} f={f} H={H} k={k}
                                      windTo={((frame.weather.wind_dir_deg + 180) % 360) * Math.PI / 180} />)}
        <g className={previewing ? "sim-nodes dimmed" : "sim-nodes"}>
        {h.nodes.map((n) => (
          <g key={n.id} transform={`translate(${n.x},${H - n.y}) scale(${k})`} className="node"
             onClick={() => selectNode(n.id)} role="button" tabIndex={0}
             aria-label={`node ${n.id}, ${NODE_STATE[frame.nodes.state[n.id]]}`}
             onKeyDown={(e) => { if (e.key === "Enter") selectNode(n.id); }}>
            <circle r={GLYPH_R + 4} className="hit" />
            {glowOpacity(frame.nodes.conc?.[n.id]) > 0
              ? <circle r={GLYPH_R + 6} className="glow" opacity={glowOpacity(frame.nodes.conc?.[n.id])} /> : null}
            <NodeGlyph state={frame.nodes.state[n.id]} selected={selected === n.id} />
          </g>
        ))}
        </g>
        {previewing ? <PreviewNodes h={h} H={H} name={preview!} /> : null}
        {layers.baselines && !previewing ? <BaselineMarks h={h} H={H} k={k} t={frame.t} /> : null}
        <WindArrow speed={frame.weather.wind_ms} fromDeg={frame.weather.wind_dir_deg} header={h} k={k} />
        <text x={0} y={H + 16 * k} className="map-label" style={{ fontSize: 13 * k }}>0</text>
        <text x={W} y={H + 16 * k} className="map-label" textAnchor="end" style={{ fontSize: 13 * k }}>{W} m</text>
      </svg>
      <figcaption className="legend">
        <span><svg width="16" height="16" viewBox="-8 -8 16 16"><circle r="4" className="glyph-normal" /></svg>normal</span>
        <span><svg width="16" height="16" viewBox="-8 -8 16 16"><circle r="6" className="glyph-elevated" /></svg>elevated</span>
        <span><svg width="16" height="16" viewBox="-8 -8 16 16"><circle r="5" className="glyph-ember" /></svg>candidate (pulsing)</span>
        <span><svg width="20" height="20" viewBox="-10 -10 20 20"><circle r="9" className="glyph-halo" /><circle r="5" className="glyph-ember" /></svg>confirmed</span>
        <span><svg width="16" height="16" viewBox="-8 -8 16 16"><path d="M-5,-5L5,5M5,-5L-5,5" className="glyph-fault" /></svg>fault</span>
        <span><svg width="16" height="16" viewBox="-8 -8 16 16"><circle r="5" className="glyph-lowpower" /></svg>low power</span>
        <span><svg width="16" height="16" viewBox="-8 -8 16 16"><rect x="-6" y="-6" width="12" height="12" className="gateway" /></svg>gateway</span>
        <span><svg width="18" height="18" viewBox="-9 -9 18 18"><circle r="8" className="glow" opacity="0.6" /><circle r="4" className="glyph-normal" /></svg>glow = smoke signal at the node</span>
        <span><svg width="16" height="16" viewBox="-8 -8 16 16"><path d="M0,-7L5,0L0,7L-5,0Z" className="fire-core" /></svg>fire (arrow: wind)</span>
      </figcaption>
    </figure>
  );
}
