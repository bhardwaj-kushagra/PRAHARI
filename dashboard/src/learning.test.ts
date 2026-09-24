import { describe, expect, it } from "vitest";
import { curvePoints, type Learning, monotoneWithinNoise } from "./learning";

const pt = (K: number, rate: number, rule = "fit") =>
  ({ K, rule, confirmed: Math.round(rate * 100), fires: 100, rate, ci95: [rate - 0.08, rate + 0.08] as [number, number],
     latency_median_min: 60, false_incidents: 3 });
const base = { label: "SIMULATION", train_seeds: [41], test_seeds: [51], train_fires: 60, test_days: 90,
               fa_budget_per_month: 3, k_min: 10, features: [], bound: pt(0, 0.6, "bound") };

describe("learning curve (M36)", () => {
  it("orders points by K and marks those that still use the bound", () => {
    const l: Learning = { ...base, rows: [pt(20, 0.7), pt(5, 0.6, "bound (K < k_min)"), pt(10, 0.65)] };
    expect(curvePoints(l).map((p) => [p.K, p.fitted, p.label])).toEqual([[5, false, "60/100"], [10, true, "65/100"], [20, true, "70/100"]]);
  });
  it("accepts dips within the interval and rejects larger drops", () => {
    expect(monotoneWithinNoise(curvePoints({ ...base, rows: [pt(5, 0.6), pt(10, 0.57), pt(20, 0.7)] }))).toBe(true);
    expect(monotoneWithinNoise(curvePoints({ ...base, rows: [pt(5, 0.6), pt(10, 0.4)] }))).toBe(false);
  });
});
