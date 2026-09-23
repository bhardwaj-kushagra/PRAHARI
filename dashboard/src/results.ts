// Experiment summary (results/summary.json from `prahari experiment`) and chart-data builders (Phase 4).

export interface Interval { rate: number; ci95: [number, number] }
export interface PipelineResult {
  false_incidents_per_month: Interval & { count: number; days: number; per_seed: number[] };
  confirmed_within_3h: { k: number; n: number; rate: number | null; ci95: [number, number] };
  latency_median_min: number | null;
}
export interface ReferenceRow {
  false_incidents_per_month: number; ci95: [number, number]; confirmed_within_3h: number; confirmed_ci95: [number, number];
}
export interface Summary {
  label: string; preset: string; scenario: string; seeds: number[]; n_nodes: number; spacing_m: number;
  days: { calibration: number; tuning: number; test: number };
  pipelines: Record<string, PipelineResult>;
  reference?: { source: string; pipelines: Record<string, ReferenceRow> };
  node?: NodeSummary;
}

// Phase 5: node-layer statistics from the quiet pass (M26 exceedance, M28 replay-tuned candidates).
export interface NodeSeed {
  seed: number; exceed: number | null; p_min: number; cand_per_node_30d: number; local_cand_per_node_30d: number;
  cm_time_frac_test: number; h: number; h_tuned: boolean; h_at_cap: boolean; p1t_h: number; p1t_at_cap: boolean;
}
export interface NodeSummary {
  per_seed: NodeSeed[]; exceed_mean: number; local_cand_mean: number; local_cand_median: number; h_mean: number;
  targets: { exceed_p: number; exceed: [number, number]; local_cand_per_node_30d: [number, number] };
  pass: { exceed: boolean; local_cand: boolean };
}
export interface NodeRow { label: string; exceed: string; local: string; all: string; h: string; p1t: string; cm: string }

const pct = (v: number | null) => (v === null ? "—" : `${(v * 100).toFixed(2)}%`);
const inBand = (v: number, [lo, hi]: [number, number]) => v >= lo && v <= hi;

/** Table rows for the node layer: one per seed, then the mean with each value checked against its target band. */
export function nodeRows(n: NodeSummary): NodeRow[] {
  const t = n.targets;
  const mark = (v: number, band: [number, number]) => (inBand(v, band) ? " ✓" : " ✗");
  const rows = n.per_seed.map((r) => ({
    label: `seed ${r.seed}`, exceed: pct(r.exceed), local: r.local_cand_per_node_30d.toFixed(2),
    all: r.cand_per_node_30d.toFixed(2), h: `${r.h.toFixed(1)}${r.h_at_cap ? " (cap)" : ""}`,
    p1t: `${r.p1t_h.toFixed(1)}${r.p1t_at_cap ? " (cap)" : ""}`, cm: pct(r.cm_time_frac_test),
  }));
  rows.push({
    label: "mean", exceed: pct(n.exceed_mean) + mark(n.exceed_mean, t.exceed),
    local: n.local_cand_mean.toFixed(2) + mark(n.local_cand_mean, t.local_cand_per_node_30d),
    all: "", h: n.h_mean.toFixed(1), p1t: "", cm: "",
  });
  rows.push({
    label: "target", exceed: `${pct(t.exceed[0])}–${pct(t.exceed[1])}`,
    local: `${t.local_cand_per_node_30d[0]}–${t.local_cand_per_node_30d[1]}`, all: "", h: "", p1t: "", cm: "",
  });
  return rows;
}

export const PIPELINE_LABEL: Record<string, string> = {
  P0: "P0 fixed threshold", P1: "P1 v1 as written", P1t: "P1t v1 replay-tuned", P2: "P2 PRAHARI",
};

export interface Row {
  name: string; label: string; y: number; mean: number; lo: number; hi: number; perSeed: number[];
  ref?: { mean: number; lo: number; hi: number };
}

/** One row per pipeline for the false-alarm chart: our mean, M45 interval, per-seed values and the report's interval. */
export function falseAlarmRows(s: Summary): Row[] {
  return Object.entries(s.pipelines).map(([name, p], y) => {
    const r = s.reference?.pipelines[name];
    const fa = p.false_incidents_per_month;
    return {
      name, label: PIPELINE_LABEL[name] ?? name, y, mean: fa.rate, lo: fa.ci95[0], hi: fa.ci95[1], perSeed: fa.per_seed,
      ref: r ? { mean: r.false_incidents_per_month, lo: r.ci95[0], hi: r.ci95[1] } : undefined,
    };
  });
}

/** Detection rows: confirmed within 3 h with the Wilson interval (M44), and the report's where available. */
export function detectionRows(s: Summary): Row[] {
  return Object.entries(s.pipelines).map(([name, p], y) => {
    const r = s.reference?.pipelines[name];
    const d = p.confirmed_within_3h;
    return {
      name, label: PIPELINE_LABEL[name] ?? name, y, mean: d.rate ?? 0, lo: d.ci95[0], hi: d.ci95[1], perSeed: [],
      ref: r ? { mean: r.confirmed_within_3h, lo: r.confirmed_ci95[0], hi: r.confirmed_ci95[1] } : undefined,
    };
  });
}

/** Log-axis bounds that include every value, snapped outward to powers of ten. */
export function logBounds(rows: Row[]): [number, number] {
  const vals = rows.flatMap((r) => [r.lo, r.hi, ...r.perSeed, ...(r.ref ? [r.ref.lo, r.ref.hi] : [])]).filter((v) => v > 0);
  if (!vals.length) return [1, 10];
  return [10 ** Math.floor(Math.log10(Math.min(...vals))), 10 ** Math.ceil(Math.log10(Math.max(...vals)))];
}
