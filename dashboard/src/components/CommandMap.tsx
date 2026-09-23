import type { FireState, Header } from "../types";
import { NODE_STATE } from "../types";
import { useFrame, useSim } from "../store";

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

function Fire({ f, H }: { f: FireState; H: number }) {
  const r = Math.max(6, Math.sqrt(f.area_m2 / Math.PI));
  return (
    <g transform={`translate(${f.x},${H - f.y})`} className="fire">
      <circle r={r} className="fire-perimeter" />
      <path d="M0,-9L7,0L0,9L-7,0Z" className="fire-core" />
      <text y={-r - 6} className="map-label" textAnchor="middle">fire {f.id} · {Math.round(f.age_min)} min</text>
    </g>
  );
}

function WindArrow({ speed, fromDeg, header }: { speed: number; fromDeg: number; header: Header }) {
  const to = ((fromDeg + 180) % 360) * (Math.PI / 180);
  const len = 36;
  const dx = Math.sin(to) * len;
  const dy = -Math.cos(to) * len;             // SVG y points down; north is up
  const x0 = header.map.width_m + 85;          // in the right-hand margin, clear of the network
  const y0 = 60;
  return (
    <g className="wind" aria-label={`wind ${speed} m/s from ${fromDeg} degrees`}>
      <circle cx={x0} cy={y0} r={44} className="wind-dial" />
      <line x1={x0 - dx / 2} y1={y0 - dy / 2} x2={x0 + dx / 2} y2={y0 + dy / 2} className="wind-line" markerEnd="url(#arrow)" />
      <text x={x0} y={y0 + 62} textAnchor="middle" className="map-label">wind {speed} m/s</text>
      <text x={x0} y={y0 + 80} textAnchor="middle" className="map-label">from {fromDeg}°</text>
    </g>
  );
}

export function CommandMap() {
  const source = useSim((s) => s.source);
  const selected = useSim((s) => s.selectedNode);
  const selectNode = useSim((s) => s.selectNode);
  const frame = useFrame();
  if (!source || !frame) return <div className="map-empty">Open a recording to see the network.</div>;
  const h = source.header;
  const W = h.map.width_m;
  const H = h.map.height_m;
  return (
    <figure className="map">
      <svg viewBox={`-20 -20 ${W + 190} ${H + 40}`} role="img" aria-label="Command map of the simulated forest and sensor network">
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
        {h.gateways.map((g) => (
          <g key={g.id} transform={`translate(${g.x},${H - g.y})`}>
            <rect x={-8} y={-8} width={16} height={16} className="gateway" />
            <text y={-14} textAnchor="middle" className="map-label">{g.id}</text>
          </g>
        ))}
        {frame.fires.map((f) => <Fire key={f.id} f={f} H={H} />)}
        {h.nodes.map((n) => (
          <g key={n.id} transform={`translate(${n.x},${H - n.y})`} className="node"
             onClick={() => selectNode(n.id)} role="button" tabIndex={0}
             aria-label={`node ${n.id}, ${NODE_STATE[frame.nodes.state[n.id]]}`}
             onKeyDown={(e) => { if (e.key === "Enter") selectNode(n.id); }}>
            <circle r={GLYPH_R + 4} className="hit" />
            <NodeGlyph state={frame.nodes.state[n.id]} selected={selected === n.id} />
          </g>
        ))}
        <WindArrow speed={frame.weather.wind_ms} fromDeg={frame.weather.wind_dir_deg} header={h} />
        <text x={0} y={H + 16} className="map-label">0</text>
        <text x={W} y={H + 16} className="map-label" textAnchor="end">{W} m</text>
      </svg>
      <figcaption className="legend">
        <span><svg width="16" height="16" viewBox="-8 -8 16 16"><circle r="4" className="glyph-normal" /></svg>normal</span>
        <span><svg width="16" height="16" viewBox="-8 -8 16 16"><circle r="6" className="glyph-elevated" /></svg>elevated</span>
        <span><svg width="16" height="16" viewBox="-8 -8 16 16"><circle r="5" className="glyph-ember" /></svg>candidate (pulsing)</span>
        <span><svg width="20" height="20" viewBox="-10 -10 20 20"><circle r="9" className="glyph-halo" /><circle r="5" className="glyph-ember" /></svg>confirmed</span>
        <span><svg width="16" height="16" viewBox="-8 -8 16 16"><path d="M-5,-5L5,5M5,-5L-5,5" className="glyph-fault" /></svg>fault</span>
        <span><svg width="16" height="16" viewBox="-8 -8 16 16"><circle r="5" className="glyph-lowpower" /></svg>low power</span>
        <span><svg width="16" height="16" viewBox="-8 -8 16 16"><rect x="-6" y="-6" width="12" height="12" className="gateway" /></svg>gateway</span>
      </figcaption>
    </figure>
  );
}
