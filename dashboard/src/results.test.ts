import { describe, expect, it } from "vitest";
import { detectionRows, falseAlarmRows, logBounds, type Summary } from "./results";

const summary: Summary = {
  label: "SIMULATION", preset: "golden", scenario: "golden_legacy", seeds: [11, 22], n_nodes: 100, spacing_m: 70,
  days: { calibration: 14, tuning: 14, test: 30 },
  pipelines: {
    P0: { false_incidents_per_month: { rate: 300, ci95: [285, 316], count: 600, days: 60, per_seed: [250, 350] },
          confirmed_within_3h: { k: 90, n: 100, rate: 0.9, ci95: [0.83, 0.94] }, latency_median_min: 9 },
    P1: { false_incidents_per_month: { rate: 130, ci95: [120, 141], count: 260, days: 60, per_seed: [120, 140] },
          confirmed_within_3h: { k: 98, n: 100, rate: 0.98, ci95: [0.93, 0.99] }, latency_median_min: 20 },
  },
  reference: { source: "report", pipelines: { P0: { false_incidents_per_month: 291, ci95: [277, 307],
                                                     confirmed_within_3h: 0.95, confirmed_ci95: [0.93, 0.97] } } },
};

describe("results chart data", () => {
  it("builds one row per pipeline with our interval, per-seed values and the report reference", () => {
    const rows = falseAlarmRows(summary);
    expect(rows.map((r) => [r.name, r.y, r.mean])).toEqual([["P0", 0, 300], ["P1", 1, 130]]);
    expect(rows[0].ref).toEqual({ mean: 291, lo: 277, hi: 307 });
    expect(rows[1].ref).toBeUndefined();
    expect(rows[0].label).toBe("P0 fixed threshold");
  });

  it("builds detection rows from the Wilson intervals", () => {
    const d = detectionRows(summary);
    expect(d[1]).toMatchObject({ mean: 0.98, lo: 0.93, hi: 0.99 });
    expect(d[0].ref).toEqual({ mean: 0.95, lo: 0.93, hi: 0.97 });
  });

  it("snaps log bounds outward to powers of ten", () => {
    expect(logBounds(falseAlarmRows(summary))).toEqual([100, 1000]);
    expect(logBounds([])).toEqual([1, 10]);
  });
});
