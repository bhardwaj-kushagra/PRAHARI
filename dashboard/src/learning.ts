/** Phase 9 — learning curve (M36) and calibration maturity (M26), from results/learning.json via summary.json. */
export interface LearnPoint {
  K?: number; rule?: string; n_pos?: number; n_neg?: number; confirmed: number; fires: number; rate: number | null;
  ci95: [number, number]; latency_median_min: number | null; false_incidents: number;
}
export interface MaturityRow {
  cal_days: number; n_cal: number; p_min: number; candidate_rate: number | null; candidate_ci95: [number, number];
  candidate_latency_median_min: number | null; confirmed_rate: number | null; h: number[]; fires: number;
}
export interface Learning {
  label: string; train_seeds: number[]; test_seeds: number[]; train_fires: number; test_days: number;
  fa_budget_per_month: number; k_min: number; features: string[]; bound: LearnPoint; rows: LearnPoint[];
  legacy_quorum?: LearnPoint & { false_incidents_per_month: number };
  maturity?: { seeds: number[]; test_days: number; tuning_days: number; rows: MaturityRow[] };
}

export interface CurvePt { K: number; rate: number; lo: number; hi: number; latency: number | null; fitted: boolean; label: string }

/** One point per K, in K order; points that still use the bound (K < k_min) are marked. */
export function curvePoints(l: Learning): CurvePt[] {
  return l.rows.filter((r) => r.rate !== null && r.K !== undefined).sort((a, b) => a.K! - b.K!).map((r) => ({
    K: r.K!, rate: r.rate!, lo: r.ci95[0], hi: r.ci95[1], latency: r.latency_median_min, fitted: r.rule === "fit",
    label: `${r.confirmed}/${r.fires}`,
  }));
}

/** Acceptance 2 — monotone within noise: no step down larger than the 95% interval half-width of the later point. */
export function monotoneWithinNoise(pts: CurvePt[]): boolean {
  return pts.every((p, i) => i === 0 || p.rate >= pts[i - 1].rate - (p.hi - p.lo) / 2);
}
