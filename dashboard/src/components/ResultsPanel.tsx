import { useEffect, useMemo, useState } from "react";
import { ABLATION, detectionRows, PIPELINE_LABEL, falseAlarmRows, logBounds, MAIN, nodeRows, type Row, type Summary } from "../results";
import { ExperimentCharts } from "./ExperimentCharts";
import { EChart, type EOption } from "./EChart";

// Grey = baselines (SPEC §6.3); ember is reserved for PRAHARI pipelines (Phase 6+). Report values: hollow, text-2.
const C = { text: "#e8e3da", text2: "#a8a29a", line: "#2a3238", base: "#7e8790", prahari: "#f26a2e" };
const colourOf = (name: string) => (name.startsWith("P2") ? C.prahari : C.base);

function intervalOption(rows: Row[], opts: { title: string; log: boolean; unit: string; fmt: (v: number) => string;
                                              bounds: [number, number]; note?: (r: Row) => string }): EOption {
  const ours = rows.map((r) => ({ value: [r.mean, r.y + 0.12], itemStyle: { color: colourOf(r.name) }, row: r }));
  const seeds = rows.flatMap((r) => r.perSeed.map((v) => [v, r.y + 0.12]));
  const refs = rows.filter((r) => r.ref).map((r) => ({ value: [r.ref!.mean, r.y - 0.14], row: r }));
  // Value labels sit just past the interval and the per-seed ticks, so they never cover the marks.
  const ends = rows.map((r) => ({ value: [Math.min(Math.max(r.hi, ...r.perSeed), opts.bounds[1]), r.y + 0.12], row: r }));
  return {
    animation: false,
    title: { text: opts.title, left: 4, top: 2, textStyle: { color: C.text, fontSize: 13, fontWeight: 500 } },
    legend: { top: 22, right: 8, textStyle: { color: C.text2, fontSize: 11 }, itemWidth: 12, itemHeight: 8,
              data: ["this simulator (SIM)", "per seed", "report (SIM)"] },
    grid: { left: 150, right: opts.note ? 150 : 56, top: 48, bottom: 34 },
    tooltip: {
      trigger: "item", backgroundColor: "#161b1f", borderColor: C.line, textStyle: { color: C.text, fontSize: 12 },
      formatter: (p: { seriesName: string; value: number[]; data: { row?: Row } }) => {
        const r = p.data.row;
        if (p.seriesName === "this simulator (SIM)" && r)
          return `${r.label}<br/><b>${opts.fmt(r.mean)}</b> ${opts.unit} (95% CI ${opts.fmt(r.lo)}–${opts.fmt(r.hi)}) · SIM`;
        if (p.seriesName === "report (SIM)" && r?.ref)
          return `${r.label} — report<br/><b>${opts.fmt(r.ref.mean)}</b> (95% CI ${opts.fmt(r.ref.lo)}–${opts.fmt(r.ref.hi)})`;
        return `seed value ${opts.fmt(p.value[0])} ${opts.unit} · SIM`;
      },
    },
    xAxis: {
      type: opts.log ? "log" : "value", min: opts.bounds[0], max: opts.bounds[1], name: opts.unit, nameLocation: "middle",
      nameGap: 22, nameTextStyle: { color: C.text2, fontSize: 11 },
      axisLabel: { color: C.text2, fontSize: 11, formatter: opts.fmt }, splitLine: { lineStyle: { color: C.line } },
      axisLine: { onZero: false, lineStyle: { color: C.line } },
    },
    yAxis: {
      type: "value", min: -0.6, max: rows.length - 0.4, inverse: true,
      axisLabel: { color: C.text, fontSize: 12, customValues: rows.map((r) => r.y),
                   formatter: (v: number) => rows[Math.round(v)]?.label ?? "" },
      splitLine: { show: false }, axisLine: { lineStyle: { color: C.line } }, axisTick: { show: false },
    },
    series: [
      { name: "per seed", type: "scatter", symbol: "rect", symbolSize: [2, 10], data: seeds,
        itemStyle: { color: C.text2, opacity: 0.8 }, z: 2 },
      { name: "labels", type: "scatter", symbolSize: 0, data: ends, silent: true, z: 5,
        label: { show: true, position: "right", distance: 6, color: C.text, fontSize: 12,
                 formatter: (p: { data: { row: Row } }) =>
                   opts.fmt(p.data.row.mean) + (opts.note ? opts.note(p.data.row) : "") } },
      { name: "this simulator (SIM)", type: "scatter", symbolSize: 11, data: ours, z: 4, itemStyle: { color: C.base },
        markLine: { silent: true, symbol: "none", label: { show: false }, lineStyle: { color: C.base, width: 2, type: "solid" },
                    data: rows.map((r) => [{ coord: [r.lo, r.y + 0.12] }, { coord: [r.hi, r.y + 0.12] }]) } },
      { name: "report (SIM)", type: "scatter", symbol: "diamond", symbolSize: 11, data: refs, z: 3,
        itemStyle: { color: "transparent", borderColor: C.text2, borderWidth: 1.5 },
        markLine: { silent: true, symbol: "none", label: { show: false }, lineStyle: { color: C.text2, width: 1.5, type: "dashed" },
                    data: rows.filter((r) => r.ref).map((r) => [{ coord: [r.ref!.lo, r.y - 0.14] }, { coord: [r.ref!.hi, r.y - 0.14] }]) } },
    ],
  };
}

/** Results view v1 (SPEC §6.2 view 6): false incidents per month (M45) and detection (M44) by pipeline. */
export function ResultsPanel() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}results/summary.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setSummary)
      .catch(() => setError("No results yet — run `prahari experiment --preset golden`, then restart the dashboard."));
  }, []);
  const fa = useMemo(() => (summary ? falseAlarmRows(summary, MAIN) : []), [summary]);
  const det = useMemo(() => (summary ? detectionRows(summary, MAIN) : []), [summary]);
  const abl = useMemo(() => (summary ? falseAlarmRows(summary, ABLATION) : []), [summary]);
  const opts = useMemo(() => ({
    fa: intervalOption(fa, { title: "False incidents per month (quiet pass, M46; 95% CI M45)", log: true,
                             unit: "per month", fmt: (v) => (v >= 10 ? v.toFixed(0) : v.toFixed(1)), bounds: logBounds(fa) }),
    det: intervalOption(det, { title: "Fires confirmed within 3 h (fire pass; 95% CI M44)", log: false, unit: "share",
                               fmt: (v) => `${Math.round(v * 100)}%`, bounds: [0, 1] }),
    abl: intervalOption(abl, { title: "Ablation: PRAHARI with one mechanism replaced by its stub", log: true,
                               unit: "false incidents per month", fmt: (v) => (v >= 10 ? v.toFixed(0) : v.toFixed(1)),
                               bounds: logBounds(abl), note: (r) => {
                                 const c = summary?.pipelines[r.name]?.confirmed_within_3h.rate;
                                 return c === null || c === undefined ? "" : ` · ${Math.round(c * 100)}% confirmed`;
                               } }),
  }), [fa, det, abl, summary]);

  if (error) return <p className="muted">{error}</p>;
  if (!summary) return <p className="muted">Loading results…</p>;
  const d = summary.days;
  const h = 80 + fa.length * 64;
  return (
    <div className="results" data-testid="results">
      <h2>Results · {summary.preset} <span className="muted small">{summary.scenario}</span></h2>
      <EChart option={opts.fa} height={h} testId="chart-false-alarms" />
      <EChart option={opts.det} height={h} testId="chart-detection" />
      <table className="results-table">
        <thead><tr><th>Pipeline</th><th>False incidents / month</th><th>Per seed</th><th>Confirmed ≤ 3 h</th><th>Median latency</th></tr></thead>
        <tbody>
          {Object.entries(summary.pipelines).map(([name, p]) => (
            <tr key={name}>
              <td>{PIPELINE_LABEL[name] ?? name}</td>
              <td className="mono">{p.false_incidents_per_month.rate.toFixed(1)} ({p.false_incidents_per_month.ci95.map((v) => v.toFixed(0)).join("–")})</td>
              <td className="mono small">{p.false_incidents_per_month.per_seed.map((v) => v.toFixed(0)).join(" · ")}</td>
              <td className="mono">{p.confirmed_within_3h.k}/{p.confirmed_within_3h.n}</td>
              <td className="mono">{p.latency_median_min ?? "—"} min</td>
            </tr>
          ))}
        </tbody>
      </table>
      {summary.reference ? <p className="muted small">Hollow diamonds: {summary.reference.source}</p> : null}
      {abl.length > 1 ? (
        <section data-testid="ablation">
          <EChart option={opts.abl} height={80 + abl.length * 64} testId="chart-ablation" />
          <p className="chart-foot">SIMULATION · seeds {(summary.sources?.ablation?.seeds ?? summary.seeds).join(", ")} ·
            {" "}{d.calibration} + {d.tuning} + {d.test} simulated days per seed · SCMR and RAQ ablations replayed from P2's runs</p>
        </section>
      ) : null}
      <ExperimentCharts summary={summary} />
      {summary.node ? (
        <>
          <h2>Node layer <span className="muted small">quiet pass, held-out test days (M26, M28)</span></h2>
          <table className="results-table" data-testid="node-table">
            <thead><tr><th></th><th>p ≤ {summary.node.targets.exceed_p} share</th><th>Local false cand. / node / 30 d</th>
              <th>All cand. / node / 30 d</th><th>Tuned h</th><th>P1t h</th><th>Common-mode time</th></tr></thead>
            <tbody>
              {nodeRows(summary.node).map((r) => (
                <tr key={r.label}><td>{r.label}</td><td className="mono">{r.exceed}</td><td className="mono">{r.local}</td>
                  <td className="mono">{r.all}</td><td className="mono">{r.h}</td><td className="mono">{r.p1t}</td>
                  <td className="mono">{r.cm}</td></tr>
              ))}
            </tbody>
          </table>
          <p className="muted small">
            Targets are the SPEC §7 Phase 5 acceptance criteria. Local candidates exclude common-mode periods (≥ 25% of
            nodes with slow z ≥ 3, ±60 min), which the edge layer handles; "(cap)" marks h at the bisection's 400 limit.
          </p>
        </>
      ) : null}
      <p className="chart-foot">
        SIMULATION · seeds {summary.seeds.join(", ")} · {d.calibration} + {d.tuning} + {d.test} simulated days per seed ·
        {" "}{summary.n_nodes} nodes at {summary.spacing_m} m · legacy mode
      </p>
    </div>
  );
}
