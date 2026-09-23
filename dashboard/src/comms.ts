import type { FrameSource } from "./sources/FrameSource";
import type { Frame, Packet } from "./types";

/** Phase 8 map helpers (M38–M43): recent packets for the animation and the state-of-charge gauge. */

export interface RecentPacket extends Packet { at: number; age: number }

/** Packets sent in (t − windowMin, t], newest first; carried packets keep their own minute (`pk.t`). */
export function recentPackets(source: FrameSource, t: number, windowMin: number): RecentPacket[] {
  const out: RecentPacket[] = [];
  for (let i = source.indexAt(t); i >= 0; i--) {
    const f = source.frameAt(i);
    if (f.t > t) continue;
    if (t - f.t > windowMin + 60) break;
    for (const pk of f.packets) {
      const at = pk.t ?? f.t;
      if (at <= t && t - at < windowMin) out.push({ ...pk, at, age: t - at });
    }
  }
  return out;
}

/** Packet outcome for styling and the legend: delivered, lost to a collision, or waiting at the node. */
export function packetOutcome(pk: Packet): "delivered" | "lost" | "queued" {
  if (pk.queued) return "queued";
  return pk.ok ? "delivered" : "lost";
}

export const MODE_NAME = ["standard", "ULP scanning", "off (stored energy below 5%)"] as const;

/** SVG arc for a ring gauge of radius r filled clockwise from 12 o'clock to fraction `v` (0–1). */
export function gaugeArc(v: number, r: number): string {
  const f = Math.max(0, Math.min(0.9999, v));
  const a = 2 * Math.PI * f;
  const x = r * Math.sin(a);
  const y = -r * Math.cos(a);
  return `M0,${-r}A${r},${r} 0 ${f > 0.5 ? 1 : 0} 1 ${x.toFixed(2)},${y.toFixed(2)}`;
}

/** Whether a recording carries the Phase 8 radio and energy models (real comms or energy). */
export function hasPhase8(frame: Frame | null): { comms: boolean; energy: boolean } {
  return { comms: !!frame?.nodes.queue, energy: !!frame?.nodes.mode };
}
