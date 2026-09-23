// Phase 6 helpers: replay variants for the mechanism switches, live run counters, the escalation ladder.
import type { Frame, NodeInfo } from "./types";

export const LADDER = ["WATCH", "CANDIDATE", "CONFIRMED", "ESCALATED"] as const;
export const SWITCHES = ["ttc", "qcc", "scmr", "raq", "srp"] as const;   // SPEC View 5
export type Switch = (typeof SWITCHES)[number];

const EXT = ".prs.jsonl.gz";

/** A recording's base scenario name: "node_mature__scmr-stub.prs.jsonl.gz" → "node_mature". */
export function baseName(name: string): string {
  return name.replace(EXT, "").replace(/\.prs\.jsonl$/, "").split("__")[0];
}

/** The module switched off in a variant recording, if any: "…__scmr-stub…" → { module: "scmr", state: "stub" }. */
export function variantOf(name: string): { module: string; state: string } | null {
  const m = /__([a-z0-9_]+)-(real|stub|off)/.exec(name);
  return m ? { module: m[1], state: m[2] } : null;
}

/** Name of the pre-recorded variant with `module` in `state`; the base recording when state is "real". */
export function variantName(name: string, module: string, state: string): string {
  return state === "real" ? baseName(name) + EXT : `${baseName(name)}__${module}-${state}${EXT}`;
}

export interface Counters { falseAlarms: number; fires: number; detected: number; medianLatency: number | null }

/** Live counters up to frame index `upto` (SPEC View 5): an alert involving a node within `radius` m of a fire that
 *  started at most `window` minutes earlier detects it (M46); any other alert counts as false. */
export function runCounters(frames: Frame[], nodes: NodeInfo[], upto: number, radius = 150, window = 180): Counters {
  const fires: { t: number; x: number; y: number; lat: number | null }[] = [];
  let falseAlarms = 0;
  for (let i = 0; i <= Math.min(upto, frames.length - 1); i++) {
    const f = frames[i];
    for (const e of f.events) if (e.type === "ignition") fires.push({ t: f.t, x: e.x ?? 0, y: e.y ?? 0, lat: null });
    for (const a of f.alerts) {
      const near = fires.filter((fi) => f.t >= fi.t && f.t - fi.t <= window &&
        a.cluster.some((n) => Math.hypot(nodes[n].x - fi.x, nodes[n].y - fi.y) <= radius));
      if (!near.length) falseAlarms++;
      for (const fi of near) if (fi.lat === null) fi.lat = f.t - fi.t;
    }
  }
  const lats = fires.map((f) => f.lat).filter((v): v is number => v !== null).sort((a, b) => a - b);
  const mid = lats.length ? (lats.length % 2 ? lats[(lats.length - 1) / 2] : (lats[lats.length / 2 - 1] + lats[lats.length / 2]) / 2) : null;
  return { falseAlarms, fires: fires.length, detected: lats.length, medianLatency: mid };
}

/** Position on a log scale in [0, 1] between lo and hi (for the SCMR gauge and the Bayes bar). */
export function logPos(v: number, lo: number, hi: number): number {
  if (!(v > 0)) return 0;
  return Math.max(0, Math.min(1, (Math.log10(v) - Math.log10(lo)) / (Math.log10(hi) - Math.log10(lo))));
}
