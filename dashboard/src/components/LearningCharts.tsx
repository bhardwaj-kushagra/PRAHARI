import { useMemo } from "react";
import { curvePoints, type CurvePt, type Learning, type MaturityRow, monotoneWithinNoise } from "../learning";
import { EChart, type EOption } from "./EChart";

// PRAHARI wears ember (SPEC §6.3); the bound it replaces is a grey dashed reference. One hue per chart: each point is
// named on its axis, so colour carries no identity here.
const C = { text: "#e8e3da", text2: "#a8a29a", line: "#2a3238", prahari: "#f26a2e", bg: "#161b1f" };
const tip = { backgroundColor: C.bg, borderColor: C.line, textStyle: { color: C.text, fontSize: 12 } };
const title = (text: string, left: number | string) =>
  ({ text, left, top: 2, textStyle: { color: C.text, fontSize: 12, fontWeight: 500 } });
const catAxis = (cats: string[], grid: number, name: string) => ({
  type: "category" as const, data: cats, gridIndex: grid, name, nameLocation: "middle" as const, nameGap: 26,
  nameTextStyle: { color: C.text2, fontSize: 11 }, axisLabel: { color: C.text, fontSize: 11, interval: 0 },
  axisTick: { show: false }, axisLine: { lineStyle: { color: C.line } },
});
const valAxis = (grid: number, extra: object) => ({
  gridIndex: grid, axisLabel: { color: C.text2, fontSize: 11 }, splitLine: { lineStyle: { color: C.line } },
  axisLine: { show: false }, nameTextStyle: { color: C.text2, fontSize: 11 }, ...extra,
});

/** M36 learning curve as two small multiples sharing the K axis: confirmation rate at the fixed false-alarm budget
 *  (95% interval, M44) and median minutes to confirm. Hollow points still use the bound (K < k_min). */
function learningOption(pts: CurvePt[], bound: Learning["bound"]): EOption {
  const cats = pts.map((p) => String(p.K));
  const dot = (p: CurvePt) => ({ color: p.fitted ? C.prahari : C.bg, borderColor: C.prahari, borderWidth: 2 });
  return {
    animation: false,
    title: [title("Confirmed within 3 h at the budget", 4), title("Median minutes to confirm", "54%")],
    grid: [{ left: 48, right: "54%", top: 34, bottom: 44 }, { left: "58%", right: 16, top: 34, bottom: 44 }],
    tooltip: { trigger: "item", ...tip, formatter: (p: { data: { pt?: CurvePt } }) => {
      const d = p.data.pt;
      return d ? `K = ${d.K} burns · ${d.fitted ? "fitted LR (M36)" : "bound (K < k_min)"}<br/>confirmed ` +
        `<b>${Math.round(d.rate * 100)}%</b> (${d.label}; 95% CI ${Math.round(d.lo * 100)}–${Math.round(d.hi * 100)}%)` +
        `<br/>median ${d.latency ?? "—"} min · SIM` : "";
    } },
    xAxis: [catAxis(cats, 0, "controlled burns in training (K)"), catAxis(cats, 1, "controlled burns in training (K)")],
    yAxis: [valAxis(0, { type: "value", min: 0, max: 1, axisLabel: { color: C.text2, fontSize: 11, formatter: (v: number) => `${v * 100}%` } }),
            valAxis(1, { type: "value", scale: true, max: (v: { max: number }) => Math.ceil(v.max * 1.08) })],
    series: [
      { type: "line", xAxisIndex: 0, yAxisIndex: 0, symbol: "circle", symbolSize: 10, lineStyle: { color: C.prahari, width: 2 },
        data: pts.map((p) => ({ value: p.rate, pt: p, itemStyle: dot(p) })),
        label: { show: true, position: "top", distance: 10, color: C.text, fontSize: 11,
                 formatter: (q: { data: { pt: CurvePt } }) => `${Math.round(q.data.pt.rate * 100)}%` },
        markLine: { silent: true, symbol: "none", data: [
          ...pts.map((p, i) => [{ coord: [i, p.lo], lineStyle: { color: C.prahari, width: 1.5, type: "solid" as const } },
                                { coord: [i, p.hi] }]),
          ...(bound.rate !== null ? [{ yAxis: bound.rate, lineStyle: { color: C.text2, type: "dashed" as const, width: 1.5 },
                                       label: { show: true, position: "insideEndBottom" as const, color: C.text2, fontSize: 10,
                                                formatter: `SBB bound ${Math.round(bound.rate * 100)}%` } }] : []),
        ], label: { show: false } } },
      { type: "line", xAxisIndex: 1, yAxisIndex: 1, symbol: "circle", symbolSize: 10, lineStyle: { color: C.prahari, width: 2 },
        data: pts.map((p) => ({ value: p.latency, pt: p, itemStyle: dot(p) })),
        label: { show: true, position: "top", distance: 8, color: C.text, fontSize: 11,
                 formatter: (q: { data: { pt: CurvePt } }) => `${q.data.pt.latency ?? "—"}` },
        markLine: bound.latency_median_min !== null ? { silent: true, symbol: "none", data: [{ yAxis: bound.latency_median_min,
          lineStyle: { color: C.text2, type: "dashed" as const, width: 1.5 },
          label: { show: true, position: "insideEndBottom" as const, color: C.text2, fontSize: 10, formatter: `bound ${bound.latency_median_min}` } }] } : undefined },
    ],
  };
}

/** M26 calibration maturity as two small multiples: the conformal floor p_min = 1/(n + 1) on a log axis (DER, from
 *  the calibration-set size) and the median minutes from ignition to the first node candidate (SIM runs). */
function maturityOption(rows: MaturityRow[]): EOption {
  const cats = rows.map((r) => `${r.cal_days} d`);
  const item = { color: C.prahari, borderColor: C.bg, borderWidth: 2 };
  return {
    animation: false,
    title: [title("QCC floor p_min (log)", 4), title("Median minutes to first node candidate", "54%")],
    grid: [{ left: 56, right: "54%", top: 34, bottom: 44 }, { left: "58%", right: 16, top: 34, bottom: 44 }],
    tooltip: { trigger: "item", ...tip, formatter: (p: { data: { r?: MaturityRow } }) => {
      const r = p.data.r;
      return r ? `${r.cal_days} days of quiet data · ${r.n_cal} scores per node and bin<br/>p_min <b>${r.p_min.toExponential(1)}</b>` +
        ` · candidates for ${Math.round((r.candidate_rate ?? 0) * 100)}% of ${r.fires} fires · median ` +
        `${r.candidate_latency_median_min ?? "—"} min · SIM` : "";
    } },
    xAxis: [catAxis(cats, 0, "days of quiet calibration data"), catAxis(cats, 1, "days of quiet calibration data")],
    yAxis: [valAxis(0, { type: "log", axisLabel: { color: C.text2, fontSize: 11, formatter: (v: number) => v.toExponential(0) } }),
            valAxis(1, { type: "value", scale: true, max: (v: { max: number }) => Math.ceil(v.max * 1.08) })],
    series: [
      { type: "line", xAxisIndex: 0, yAxisIndex: 0, symbol: "circle", symbolSize: 9, lineStyle: { color: C.prahari, width: 2 }, itemStyle: item,
        data: rows.map((r) => ({ value: r.p_min, r })),
        label: { show: true, position: "right", color: C.text, fontSize: 11, formatter: (q: { data: { r: MaturityRow } }) => q.data.r.p_min.toExponential(1) } },
      { type: "line", xAxisIndex: 1, yAxisIndex: 1, symbol: "circle", symbolSize: 9, lineStyle: { color: C.prahari, width: 2 }, itemStyle: item,
        data: rows.map((r) => ({ value: r.candidate_latency_median_min, r })),
        label: { show: true, position: "top", color: C.text, fontSize: 11, formatter: (q: { data: { r: MaturityRow } }) => `${q.data.r.candidate_latency_median_min ?? "—"}` } },
    ],
  };
}

/** Phase 9 (SPEC View 6): the system improving with evidence — burns for the edge, quiet days for the node. */
export function LearningCharts({ learning }: { learning: Learning }) {
  const pts = useMemo(() => curvePoints(learning), [learning]);
  const mat = learning.maturity;
  const lq = learning.legacy_quorum;
  if (!pts.length) return null;
  const mono = monotoneWithinNoise(pts);
  return (
    <>
      <section data-testid="learning">
        <EChart option={learningOption(pts, learning.bound)} height={270} testId="chart-learning" />
        <p className="muted small">The edge's likelihood ratio fitted from K controlled burns (M36, features
          {" "}{learning.features.join(", ")}) replaces the Sellke–Bayarri–Berger bound once K ≥ {learning.k_min}; hollow points
          still use the bound. Every rule is held to the same budget of {learning.fa_budget_per_month} false incidents per month
          on the held-out quiet runs. Monotone within noise: <b>{mono ? "yes" : "no"}</b>.
          {lq?.rate != null ? <> For reference, the deployed legacy quorum (2 nodes on dry days, 3 on wet) confirms
            {" "}{Math.round(lq.rate * 100)}% on the same runs, at its own {lq.false_incidents_per_month.toFixed(1)} false incidents
            per month.</> : null}</p>
        <p className="chart-foot">SIMULATION · training seeds {learning.train_seeds.join(", ")} ({learning.train_fires} burns) ·
          held-out seeds {learning.test_seeds.join(", ")} · {learning.test_days} simulated test days</p>
      </section>
      {mat?.rows.length ? (
        <section data-testid="maturity">
          <EChart option={maturityOption(mat.rows)} height={250} testId="chart-maturity" />
          <p className="muted small">More quiet days give each node a larger calibration set, so its conformal p-value can
            fall further (M26) and a fire's evidence crosses the node threshold sooner.</p>
          <p className="chart-foot">SIMULATION · seeds {mat.seeds.join(", ")} · calibration days as shown + {mat.tuning_days} tuning +
            {" "}{mat.test_days} test days per run · p_min from the calibration-set size (DER)</p>
        </section>
      ) : null}
    </>
  );
}
