import { useMemo } from "react";
import { decodePlume, glyphScale, lambdaToRGBA, pixelCaption, plumeToRGBA, sfColour, svgPoints } from "../layers";
import type { Frame, Header, LayoutName } from "../types";

interface LayerProps { h: Header; H: number }

/** Ignition interfaces (M2): village polygon, footpaths, road and power line, told apart by line style. */
export function InterfaceLayer({ h, H }: LayerProps) {
  const k = glyphScale(h.map.width_m);
  return (
    <g className="interfaces" aria-label="ignition interfaces">
      {h.map.interfaces.map((f, i) =>
        f.closed ? (
          <g key={i}>
            <polygon points={svgPoints(f.points, H)} className={`if if-${f.kind}`}><title>{f.kind}</title></polygon>
            <text x={centroid(f.points)[0]} y={H - centroid(f.points)[1]} textAnchor="middle" className="map-label"
                  style={{ fontSize: 13 * k }}>{f.kind}</text>
          </g>
        ) : (
          <polyline key={i} points={svgPoints(f.points, H)} className={`if if-${f.kind}`} strokeWidth={ifWidth(f.kind) * k}>
            <title>{f.kind.replace("_", " ")}</title>
          </polyline>
        ),
      )}
    </g>
  );
}

function ifWidth(kind: string): number {
  return kind === "road" ? 5 : kind === "power_line" ? 1.5 : 2;
}

function centroid(points: [number, number][]): [number, number] {
  const n = points.length;
  return [points.reduce((s, p) => s + p[0], 0) / n, points.reduce((s, p) => s + p[1], 0) / n];
}

/** Relative ignition likelihood (M3) as a one-hue heat image, drawn once per recording. */
export function LikelihoodLayer({ h }: LayerProps) {
  const lg = h.map.lambda_grid;
  const href = useMemo(() => {
    if (!lg || typeof document === "undefined") return null;
    const canvas = document.createElement("canvas");
    canvas.width = lg.nx;
    canvas.height = lg.ny;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.putImageData(new ImageData(lambdaToRGBA(lg.values, lg.nx, lg.ny), lg.nx, lg.ny), 0, 0);
    return canvas.toDataURL();
  }, [lg]);
  if (!lg || !href) return null;
  return (
    <image href={href} x={0} y={0} width={lg.nx * lg.cell_m} height={lg.ny * lg.cell_m}
           preserveAspectRatio="none" className="likelihood" aria-label="relative ignition likelihood" />
  );
}

/** Satellite pixel grid (375 m); the pixel over the network's centre is highlighted with the DER caption. */
export function SatelliteLayer({ h, H }: LayerProps) {
  const px = h.satellite_pixel_m ?? 375;
  const W = h.map.width_m;
  const k = glyphScale(W);
  const xs = [];
  for (let x = 0; x <= W; x += px) xs.push(x);
  const ys = [];
  for (let y = 0; y <= H; y += px) ys.push(y);
  // Highlight the pixel that contains the centre of the network.
  const mx = h.nodes.reduce((a, n) => a + n.x, 0) / Math.max(1, h.nodes.length);
  const my = h.nodes.reduce((a, n) => a + n.y, 0) / Math.max(1, h.nodes.length);
  const cx = Math.floor(mx / px) * px;
  const cy = Math.floor(my / px) * px;
  return (
    <g className="satellite" aria-label="satellite pixel grid">
      {xs.map((x) => <line key={`x${x}`} x1={x} y1={0} x2={x} y2={H} className="sat-line" />)}
      {ys.map((y) => <line key={`y${y}`} x1={0} y1={H - y} x2={W} y2={H - y} className="sat-line" />)}
      <rect x={cx} y={H - cy - px} width={px} height={px} className="sat-pixel" />
      <text x={cx + 6 * k} y={H - cy - px - 8 * k} className="map-label sat-caption" style={{ fontSize: 13 * k }}>
        {pixelCaption(px, h.spacing_m).text} · DER
      </text>
    </g>
  );
}

/** Node → gateway links coloured by spreading factor (M38); dashed rings mark nodes with no link. */
export function LinksLayer({ h, H }: LayerProps) {
  const L = h.links;
  if (!L) return null;
  const k = glyphScale(h.map.width_m);
  const gw = new Map(h.gateways.map((g) => [g.id, g]));
  return (
    <g className="links" aria-label="radio links by spreading factor">
      {h.nodes.map((n, i) => {
        const g = L.gateway[i] ? gw.get(L.gateway[i] as string) : undefined;
        const tip = g
          ? `node ${n.id} → ${g.id} · ${Math.round(L.d_m[i])} m · PL ${L.pl_db[i]} dB · ${L.prx_dbm[i]} dBm · SF${L.sf[i]}`
          : `node ${n.id}: no link closes (${Math.round(L.d_m[i])} m) — needs a relay (Phase 8)`;
        return g ? (
          <line key={i} x1={n.x} y1={H - n.y} x2={g.x} y2={H - g.y} stroke={sfColour(L.sf[i])}
                strokeWidth={1.2 * k} className="link"><title>{tip}</title></line>
        ) : (
          <circle key={i} cx={n.x} cy={H - n.y} r={12 * k} className="no-link" strokeWidth={1.5 * k}><title>{tip}</title></circle>
        );
      })}
    </g>
  );
}

/** Detection disks (radius r_d, M4) around the displayed layout's nodes. */
export function CoverageLayer({ h, H, nodes }: LayerProps & { nodes: [number, number][] }) {
  const r = h.detection_radius_m ?? 50;
  return (
    <g className="coverage" aria-label={`detection radius ${r} m`}>
      {nodes.map(([x, y], i) => <circle key={i} cx={x} cy={H - y} r={r} className="cover-disk" />)}
    </g>
  );
}

/** Another layout's node positions, drawn hollow: a comparison, not a simulation. */
export function PreviewNodes({ h, H, name }: LayerProps & { name: LayoutName }) {
  const k = glyphScale(h.map.width_m);
  const nodes = h.layouts?.[name]?.nodes ?? [];
  return (
    <g className="preview" aria-label={`${name} layout preview`}>
      {nodes.map(([x, y], i) => <circle key={i} cx={x} cy={H - y} r={5 * k} className="preview-node" strokeWidth={1.5 * k} />)}
    </g>
  );
}

/** Smoke concentration (active plume model, SPEC §5.5) as a one-hue heat image from the recorded grid. */
export function PlumeLayer({ frame, H }: { frame: Frame | null; H: number }) {
  const g = frame?.plume;
  const href = useMemo(() => {
    if (!g || typeof document === "undefined") return null;
    const canvas = document.createElement("canvas");
    canvas.width = g.nx;
    canvas.height = g.ny;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.putImageData(new ImageData(plumeToRGBA(decodePlume(g), g.nx, g.ny), g.nx, g.ny), 0, 0);
    return canvas.toDataURL();
  }, [g]);
  if (!g || !href) return null;
  return (
    <image href={href} x={g.x0} y={H - g.y0 - g.ny * g.cell_m} width={g.nx * g.cell_m} height={g.ny * g.cell_m}
           preserveAspectRatio="none" className="plume" aria-label={`smoke concentration, max ${g.max} su`} />
  );
}
