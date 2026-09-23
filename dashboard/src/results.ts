// Experiment summary (results/summary.json from `prahari experiment`) and chart-data builders (Phase 4).

export interface Interval { rate: number; ci95: [number, number] }
export interface PipelineResult {
  false_incidents_per_month: Interval & { count: number; days: number; per_seed: number[] };
  confirmed_within_3h: { k: number; n: number; rate: number | null; ci95: [number, number] };
  latency_median_min: number | null;
  single_node_within_3h?: { k: number; n: number; rate: number | null; ci95: [number, number] };   // Phase 7
  h_per_seed?: number[];
}
export interface ReferenceRow {
  false_incidents_per_month: number; ci95: [number, number]; confirmed_within_3h: number;
  confirmed_ci95: [number, number] | null;
}
// Phase 7 sections of the combined summary (`prahari.eval.report.combine`).
export interface DialPoint extends PipelineResult { target_per_node_30d: number; h_per_seed: number[] }
export interface SpacingRow {
  spacing_m: number; confirmed_within_3h: PipelineResult["confirmed_within_3h"];
  single_node_within_3h: PipelineResult["confirmed_within_3h"];
  false_incidents_per_month: PipelineResult["false_incidents_per_month"]; latency_median_min: number | null;
}
export interface Summary {
  label: string; preset: string; scenario: string; seeds: number[]; n_nodes: number; spacing_m: number;
  days: { calibration: number; tuning: number; test: number };
  pipelines: Record<string, PipelineResult>;
  reference?: { source: string; pipelines: Record<string, ReferenceRow>;
                spacing?: { seeds: number[]; confirmed_within_3h: Record<string, number> } };
  node?: NodeSummary;
  dial?: DialPoint[];
  spacing?: { seeds: number[]; rows: SpacingRow[] };
  sources?: Record<string, { seeds: number[] }>;
  seed_sweep?: { seeds: number[]; pipelines: Record<string, PipelineResult> };
  ablation_form?: "stub" | "legacy";
  energy?: EnergyTable;
}

/** Phase 8: M41 daily budgets per sensor mode, the M42 harvest and the M43 store (`prahari energy`). */
export interface EnergyTable {
  label: string; rows: { sensor: string; mode: string; wh_day: number; autonomy_days: number }[];
  harvest_wh_day: { clear: number; cloudy: [number, number] }; store_wh: number; frames_per_day: number;
  toa_ms: number; voltage_v: number; source: string;
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
  "P2-QCC": "P2 minus QCC", "P2-TTC": "P2 minus TTC", "P2-SCMR": "P2 minus SCMR", "P2-RAQ": "P2 minus RAQ",
};
export const MAIN = ["P0", "P1", "P1t", "P2"];
export const ABLATION = ["P2", "P2-QCC", "P2-TTC", "P2-SCMR", "P2-RAQ"];

/** Pipelines of `s` in the order of `names` (all pipelines when omitted). */
function pick(s: Summary, names?: string[]): [string, PipelineResult][] {
  const all = Object.entries(s.pipelines);
  return names ? names.filter((n) => s.pipelines[n]).map((n) => [n, s.pipelines[n]]) : all;
}

export interface Row {
  name: string; label: string; y: number; mean: number; lo: number; hi: number; perSeed: number[];
  ref?: { mean: number; lo: number; hi: number };
}

/** One row per pipeline for the false-alarm chart: our mean, M45 interval, per-seed values and the report's interval. */
export function falseAlarmRows(s: Summary, names?: string[]): Row[] {
  return pick(s, names).map(([name, p], y) => {
    const r = s.reference?.pipelines[name];
    const fa = p.false_incidents_per_month;
    return {
      name, label: PIPELINE_LABEL[name] ?? name, y, mean: fa.rate, lo: fa.ci95[0], hi: fa.ci95[1], perSeed: fa.per_seed,
      ref: r ? { mean: r.false_incidents_per_month, lo: r.ci95[0], hi: r.ci95[1] } : undefined,
    };
  });
}

/** Detection rows: confirmed within 3 h with the Wilson interval (M44), and the report's where available. */
export function detectionRows(s: Summary, names?: string[]): Row[] {
  return pick(s, names).map(([name, p], y) => {
    const r = s.reference?.pipelines[name];
    const d = p.confirmed_within_3h;
    return {
      name, label: PIPELINE_LABEL[name] ?? name, y, mean: d.rate ?? 0, lo: d.ci95[0], hi: d.ci95[1], perSeed: [],
      ref: r ? { mean: r.confirmed_within_3h, lo: r.confirmed_ci95?.[0] ?? r.confirmed_within_3h,
                 hi: r.confirmed_ci95?.[1] ?? r.confirmed_within_3h } : undefined,
    };
  });
}

/** Log-axis bounds that include every value, snapped outward to powers of ten. */
export function logBounds(rows: Row[]): [number, number] {
  const vals = rows.flatMap((r) => [r.lo, r.hi, ...r.perSeed, ...(r.ref ? [r.ref.lo, r.ref.hi] : [])]).filter((v) => v > 0);
  if (!vals.length) return [1, 10];
  return [10 ** Math.floor(Math.log10(Math.min(...vals))), 10 ** Math.ceil(Math.log10(Math.max(...vals)))];
}

// -- Phase 7: operating dial and spacing ------------------------------------------------------------------------
export interface DialPt { target: number; fa: number; lo: number; hi: number; latency: number | null; det: number | null;
                          isDefault: boolean }

/** The operating dial (SPEC View 6): false incidents per month against median latency, one point per M28 target. */
export function dialPoints(s: Summary): DialPt[] {
  return (s.dial ?? []).map((d) => ({
    target: d.target_per_node_30d, fa: d.false_incidents_per_month.rate, lo: d.false_incidents_per_month.ci95[0],
    hi: d.false_incidents_per_month.ci95[1], latency: d.latency_median_min, det: d.confirmed_within_3h.rate,
    isDefault: Math.abs(d.target_per_node_30d - 1) < 1e-9,
  }));
}

export interface SpacingPt { spacing: number; kind: "confirmed" | "single node"; mean: number; lo: number; hi: number;
                             ref?: number }

/** Spacing sweep (SPEC View 6): confirmations and single-node alerts within 3 h at each spacing, with the report's. */
export function spacingPoints(s: Summary): SpacingPt[] {
  const ref = s.reference?.spacing?.confirmed_within_3h ?? {};
  return (s.spacing?.rows ?? []).flatMap((r) => [
    { spacing: r.spacing_m, kind: "confirmed" as const, mean: r.confirmed_within_3h.rate ?? 0,
      lo: r.confirmed_within_3h.ci95[0], hi: r.confirmed_within_3h.ci95[1], ref: ref[String(r.spacing_m)] },
    { spacing: r.spacing_m, kind: "single node" as const, mean: r.single_node_within_3h.rate ?? 0,
      lo: r.single_node_within_3h.ci95[0], hi: r.single_node_within_3h.ci95[1] },
  ]);
}

/** Phase 7: how the node ablations (P2-QCC, P2-TTC) were formed — the report simulation's variants or module stubs. */
export function ablationNote(s: Summary): string {
  return s.ablation_form === "legacy"
    ? "QCC and TTC ablations in the report simulation's legacy forms"
    : "QCC and TTC ablations as module stubs";
}

export interface EnergyRow { label: string; sensor: string; wh: number; days: number; y: number }

/** Phase 8: energy chart rows, lowest budget first (bars on a log axis). */
export function energyRows(s: Summary): EnergyRow[] {
  return (s.energy?.rows ?? []).slice().sort((a, b) => a.wh_day - b.wh_day)
    .map((r, y) => ({ label: `${r.sensor} ${r.mode}`, sensor: r.sensor, wh: r.wh_day, days: r.autonomy_days, y }));
}
