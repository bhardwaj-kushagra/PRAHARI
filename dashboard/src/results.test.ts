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

describe("node-layer rows (Phase 5)", () => {
  it("lists seeds, then the mean against its targets", async () => {
    const { nodeRows } = await import("./results");
    const seed = (s: number, ex: number, loc: number) => ({ seed: s, exceed: ex, p_min: 3e-4, cand_per_node_30d: 5,
      local_cand_per_node_30d: loc, cm_time_frac_test: 0.02, h: 226.58, h_tuned: true, h_at_cap: false, p1t_h: 400,
      p1t_at_cap: true });
    const rows = nodeRows({ per_seed: [seed(11, 0.0088, 0.7), seed(22, 0.03, 2.1)], exceed_mean: 0.0194,
      local_cand_mean: 1.4, local_cand_median: 1.4, h_mean: 226.6,
      targets: { exceed_p: 0.01, exceed: [0.008, 0.02], local_cand_per_node_30d: [0.5, 1.5] },
      pass: { exceed: true, local_cand: true } });
    expect(rows.map((r) => r.label)).toEqual(["seed 11", "seed 22", "mean", "target"]);
    expect(rows[0]).toMatchObject({ exceed: "0.88%", local: "0.70", h: "226.6", p1t: "400.0 (cap)" });
    expect(rows[2].exceed).toBe("1.94% ✓");
    expect(rows[2].local).toBe("1.40 ✓");
    expect(rows[3]).toMatchObject({ exceed: "0.80%–2.00%", local: "0.5–1.5" });
  });
});

describe("Phase 7 builders", () => {
  it("orders rows by a pipeline list and skips missing ones", async () => {
    const { falseAlarmRows } = await import("./results");
    expect(falseAlarmRows(summary, ["P1", "P2", "P0"]).map((r) => [r.name, r.y])).toEqual([["P1", 0], ["P0", 1]]);
  });
  it("builds dial points and spacing points with the report's reference", async () => {
    const { dialPoints, spacingPoints } = await import("./results");
    const pr = (rate: number, k: number) => ({
      false_incidents_per_month: { rate, ci95: [rate - 1, rate + 1] as [number, number], count: 1, days: 30, per_seed: [rate] },
      confirmed_within_3h: { k, n: 10, rate: k / 10, ci95: [0.1, 0.9] as [number, number] }, latency_median_min: 60 });
    const s = { ...summary,
      dial: [{ target_per_node_30d: 0.5, h_per_seed: [260], ...pr(3, 6) }, { target_per_node_30d: 1, h_per_seed: [230], ...pr(6, 8) }],
      spacing: { seeds: [11], rows: [{ spacing_m: 70, confirmed_within_3h: pr(1, 8).confirmed_within_3h,
        single_node_within_3h: pr(1, 10).confirmed_within_3h, false_incidents_per_month: pr(1, 1).false_incidents_per_month,
        latency_median_min: 60 }] },
      reference: { source: "r", pipelines: {}, spacing: { seeds: [11], confirmed_within_3h: { "70": 0.85 } } } };
    expect(dialPoints(s).map((p) => [p.target, p.fa, p.isDefault])).toEqual([[0.5, 3, false], [1, 6, true]]);
    const sp = spacingPoints(s);
    expect(sp.map((p) => [p.kind, p.mean, p.ref])).toEqual([["confirmed", 0.8, 0.85], ["single node", 1, undefined]]);
  });
  it("names the form of the node ablations", async () => {
    const { ablationNote } = await import("./results");
    expect(ablationNote({ ...summary, ablation_form: "legacy" })).toContain("legacy forms");
    expect(ablationNote(summary)).toContain("module stubs");
  });
});
