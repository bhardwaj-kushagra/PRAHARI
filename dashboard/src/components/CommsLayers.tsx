import { gaugeArc, MODE_NAME, packetOutcome, recentPackets } from "../comms";
import { glyphScale } from "../layers";
import type { FrameSource } from "../sources/FrameSource";
import type { Frame, Header } from "../types";

interface Props { h: Header; H: number; source: FrameSource; frame: Frame }

/** Phase 8 — packet animation (M39–M40): each uplink of the last few minutes as a line from its sender to the
 *  gateway or TS011 relay, fading with age. Delivered = pine, lost to a collision = amber dashed, candidate frames
 *  thicker than heartbeats; frames waiting at a node (store-and-forward) show a count badge. */
export function PacketLayer({ h, H, source, frame }: Props) {
  const k = glyphScale(h.map.width_m);
  const window = Math.max(3, h.record_every * h.tick_minutes);
  const pks = recentPackets(source, frame.t, window);
  const gw = new Map(h.gateways.map((g) => [g.id, g]));
  const end = (to: string | null): [number, number] | null => {
    if (!to) return null;
    const g = gw.get(to);
    if (g) return [g.x, H - g.y];
    const n = h.nodes[Number(to.slice(1))];
    return n ? [n.x, H - n.y] : null;
  };
  const queue = frame.nodes.queue ?? [];
  return (
    <g className="packets" aria-label="uplink packets">
      {pks.filter((p) => !p.queued).map((p, j) => {
        const a = h.nodes[p.from];
        const b = end(p.to);
        if (!a || !b) return null;
        const out = packetOutcome(p);
        const w = (p.kind === "candidate" ? 2.6 : 1.1) * k;
        return (
          <line key={j} x1={a.x} y1={H - a.y} x2={b[0]} y2={b[1]} className={`pk pk-${out}`} strokeWidth={w}
                opacity={Math.max(0.15, 1 - p.age / window)}>
            <title>{`${p.kind ?? "frame"} · node ${p.from} → ${p.to} · SF${p.sf} · ${p.toa_ms ?? "?"} ms on air` +
                    `${p.retry ? ` · retry ${p.retry}` : ""} · ${out} · minute ${p.at} · SIM`}</title>
          </line>
        );
      })}
      {queue.map((q, i) => (q > 0 ? (
        <g key={`q${i}`} transform={`translate(${h.nodes[i].x + 11 * k},${H - h.nodes[i].y - 11 * k}) scale(${k})`}
           className="queue-badge">
          <rect x={-8} y={-7} width={16} height={14} rx={3} />
          <text textAnchor="middle" y={4}>{q}</text>
          <title>{`node ${i}: ${q} frame${q === 1 ? "" : "s"} waiting for the gateway (store-and-forward) · SIM`}</title>
        </g>
      ) : null))}
    </g>
  );
}

/** Phase 8 — state-of-charge gauges (M43): a ring around each node filled to its stored energy; pine in standard
 *  mode, amber when scanning in ULP (< 20%), grey when stopped (< 5%). */
export function SocLayer({ h, H, frame }: Omit<Props, "source">) {
  const k = glyphScale(h.map.width_m);
  const soc = frame.nodes.soc;
  const mode = frame.nodes.mode ?? [];
  return (
    <g className="soc" aria-label="state of charge">
      {h.nodes.map((n, i) => (
        <g key={i} transform={`translate(${n.x},${H - n.y}) scale(${k})`}>
          <circle r={12} className="soc-track" />
          <path d={gaugeArc(soc[i], 12)} className={`soc-arc soc-m${mode[i] ?? 0}`} />
          <title>{`node ${i} · ${Math.round(soc[i] * 100)}% stored · ${MODE_NAME[mode[i] ?? 0]} · SIM`}</title>
        </g>
      ))}
    </g>
  );
}
