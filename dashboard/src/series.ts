// Pure time-series extraction from recorded frames (Phase 2 charts). Values are SIM output as recorded.
import type { Frame } from "./types";

export interface Series { t: number[]; v: number[] }
export type WeatherKey = "T" | "RH" | "wind_ms" | "ffmc";

/** Keep at most `max` points, evenly spaced, always keeping the first and last. */
export function thin(s: Series, max = 1500): Series {
  const n = s.t.length;
  if (n <= max) return s;
  const t: number[] = [];
  const v: number[] = [];
  for (let k = 0; k < max; k++) {
    const i = Math.round((k * (n - 1)) / (max - 1));
    t.push(s.t[i]);
    v.push(s.v[i]);
  }
  return { t, v };
}

export function weatherSeries(frames: Frame[], key: WeatherKey): Series {
  return { t: frames.map((f) => f.t), v: frames.map((f) => f.weather[key]) };
}

export function hazeSeries(frames: Frame[]): Series {
  return { t: frames.map((f) => f.t), v: frames.map((f) => f.haze ?? 0) };
}

export function nodeSeries(frames: Frame[], node: number): Series {
  return { t: frames.map((f) => f.t), v: frames.map((f) => f.nodes.reading[node]) };
}

/** Intervals [start, end] (simulated minutes) where regional haze is above zero. */
export function hazeBands(frames: Frame[]): [number, number][] {
  const bands: [number, number][] = [];
  let start: number | null = null;
  for (const f of frames) {
    const on = (f.haze ?? 0) > 0;
    if (on && start === null) start = f.t;
    if (!on && start !== null) {
      bands.push([start, f.t]);
      start = null;
    }
  }
  if (start !== null) bands.push([start, frames[frames.length - 1].t]);
  return bands;
}

/** `k` node ids spread evenly across 0..n−1 (the small-multiples panel). */
export function pickNodes(n: number, k = 8): number[] {
  if (n <= k) return Array.from({ length: n }, (_, i) => i);
  return Array.from({ length: k }, (_, i) => Math.round((i * (n - 1)) / (k - 1)));
}

/** Shared y-range for small multiples, padded 5% and rounded outward to half units. */
export function sharedRange(series: Series[]): [number, number] {
  let lo = Infinity;
  let hi = -Infinity;
  for (const s of series) for (const v of s.v) { if (v < lo) lo = v; if (v > hi) hi = v; }
  if (!Number.isFinite(lo)) return [0, 1];
  const pad = (hi - lo || 1) * 0.05;
  return [Math.floor((lo - pad) * 2) / 2, Math.ceil((hi + pad) * 2) / 2];
}

/** Axis label for simulated minutes: "d2 14:00". */
export function minuteLabel(t: number): string {
  const d = Math.floor(t / 1440) + 1;
  const m = Math.floor(t % 1440);
  return `d${d} ${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
}

// -- Phase 5: node inspector series (SPEC §6.2 view 2) ------------------------------------------------
export type NodeKey = "reading" | "residual" | "p" | "cusum" | "health" | "baseline" | "soc";

/** One recorded per-node field over time; frames that lack the field (older recordings) are skipped. */
export function nodeField(frames: Frame[], key: NodeKey, node: number): Series {
  const t: number[] = [];
  const v: number[] = [];
  for (const f of frames) {
    const arr = f.nodes[key];
    if (arr && arr[node] !== undefined) { t.push(f.t); v.push(arr[node]); }
  }
  return { t, v };
}

/** M26 floor p_min = 1/(n+1) of the node's calibration set at each frame. */
export function floorSeries(frames: Frame[], node: number): Series {
  const t: number[] = [];
  const v: number[] = [];
  for (const f of frames) {
    const n = f.nodes.n_cal?.[node];
    if (n !== undefined) { t.push(f.t); v.push(1 / (n + 1)); }
  }
  return { t, v };
}

/** CUSUM threshold h in use at each frame (M28: h_default until the replay tuning completes). */
export function hSeries(frames: Frame[]): Series {
  return { t: frames.map((f) => f.t), v: frames.map((f) => f.cusum_h) };
}

/** Candidate events of one node as [t, G at the crossing] (every event tick is recorded). */
export function candidateMarks(frames: Frame[], node: number): [number, number][] {
  const out: [number, number][] = [];
  for (const f of frames) {
    if (f.events.some((e) => e.type === "candidate" && e.node === node)) out.push([f.t, f.nodes.cusum[node]]);
  }
  return out;
}
