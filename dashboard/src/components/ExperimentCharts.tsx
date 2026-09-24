import { useMemo } from "react";
import { dialPoints, type DialPt, energyRows, type EnergyRow, spacingPoints, type SpacingPt, type Summary } from "../results";
import { EChart, type EOption } from "./EChart";
import { LearningCharts } from "./LearningCharts";

// PRAHARI wears ember (SPEC §6.3); single-node alerts use the validated series blue; the report is hollow and grey.
const C = { text: "#e8e3da", text2: "#a8a29a", line: "#2a3238", prahari: "#f26a2e", series: "#3987e5" };
const tip = { backgroundColor: "#161b1f", borderColor: C.line, textStyle: { color: C.text, fontSize: 12 } };
const axis = (name: string) => ({
  name, nameLocation: "middle" as const, nameGap: 26, nameTextStyle: { color: C.text2, fontSize: 11 },
  axisLabel: { color: C.text2, fontSize: 11 }, splitLine: { lineStyle: { color: C.line } },
  axisLine: { lineStyle: { color: C.line } },
});
const rLabel = (t: number) => `1 per ${Math.round(30 / t)} d`;

/** Operating dial (SPEC View 6): each point re-tunes the node threshold (M28) for another false-candidate target. */
function dialOption(pts: DialPt[]): EOption {
  const xs = pts.flatMap((p) => [p.lo, p.hi]).filter((v) => v > 0);
  return {
    animation: false,
    title: { text: "Operating dial: false incidents against median time to confirm", left: 4, top: 2,
             textStyle: { color: C.text, fontSize: 13, fontWeight: 500 } },
    grid: { left: 60, right: 30, top: 36, bottom: 44 },
    tooltip: { trigger: "item", ...tip, formatter: (p: { data: { pt: DialPt } }) => {
      const d = p.data.pt;
      return `node target ${rLabel(d.target)} per node<br/><b>${d.fa.toFixed(1)}</b> false incidents/month ` +
             `(95% CI ${d.lo.toFixed(1)}–${d.hi.toFixed(1)})<br/>median ${d.latency ?? "—"} min · confirmed ` +
             `${d.det === null ? "—" : Math.round(d.det * 100) + "%"} · SIM`;
    } },
    xAxis: { type: "log", min: Math.max(0.1, 10 ** Math.floor(Math.log10(Math.min(...xs, 1)))),
             max: 10 ** Math.ceil(Math.log10(Math.max(...xs, 10))), ...axis("false incidents per month (log)") },
    yAxis: { type: "value", scale: true, ...axis("median minutes to confirm"), nameGap: 40 },
    series: [{
      type: "line", symbol: "circle", symbolSize: 9, lineStyle: { color: C.prahari, width: 1.5 }, itemStyle: { color: C.prahari },
      data: pts.filter((p) => p.latency !== null).map((p) => ({
        value: [p.fa, p.latency], pt: p, symbolSize: p.isDefault ? 14 : 9,
        label: { show: true, position: "right", color: C.text, fontSize: 11,
                 formatter: `${rLabel(p.target)}${p.isDefault ? " (design)" : ""}` },
      })),
    }],
  };
}

/** Node spacing (SPEC View 6): confirmations and single-node alerts within 3 h at 70, 100 and 150 m. */
function spacingOption(pts: SpacingPt[]): EOption {
  const cats = [...new Set(pts.map((p) => `${p.spacing} m`))];
  const series = (kind: SpacingPt["kind"], color: string, dx: number) => ({
    name: kind === "confirmed" ? "confirmed (edge)" : "single-node alert", type: "scatter", symbolSize: 11,
    itemStyle: { color }, data: pts.filter((p) => p.kind === kind).map((p) => ({ value: [cats.indexOf(`${p.spacing} m`) + dx, p.mean], pt: p })),
    label: { show: true, position: "right", color: C.text, fontSize: 11,
             formatter: (q: { data: { pt: SpacingPt } }) => `${Math.round(q.data.pt.mean * 100)}%` },
    markLine: { silent: true, symbol: "none", label: { show: false }, lineStyle: { color, width: 2, type: "solid" },
                data: pts.filter((p) => p.kind === kind).map((p) => [{ coord: [cats.indexOf(`${p.spacing} m`) + dx, p.lo] },
                                                                      { coord: [cats.indexOf(`${p.spacing} m`) + dx, p.hi] }]) },
  });
  return {
    animation: false,
    title: { text: "Node spacing: fires seen within 3 h (95% CI M44)", left: 4, top: 2,
             textStyle: { color: C.text, fontSize: 13, fontWeight: 500 } },
    legend: { top: 22, right: 8, textStyle: { color: C.text2, fontSize: 11 }, itemWidth: 12, itemHeight: 8,
              data: ["confirmed (edge)", "single-node alert", "report (SIM)"] },
    grid: { left: 52, right: 30, top: 50, bottom: 30 },
    tooltip: { trigger: "item", ...tip, formatter: (p: { seriesName: string; data: { pt: SpacingPt } }) =>
      `${p.data.pt.spacing} m · ${p.seriesName}<br/><b>${Math.round(p.data.pt.mean * 100)}%</b> ` +
      `(${Math.round(p.data.pt.lo * 100)}–${Math.round(p.data.pt.hi * 100)}%) · SIM` },
    xAxis: { type: "value", min: -0.5, max: cats.length - 0.5,
             axisLabel: { color: C.text, fontSize: 12, customValues: cats.map((_, i) => i),
                          formatter: (v: number) => cats[Math.round(v)] ?? "" },
             axisTick: { customValues: cats.map((_, i) => i) },
             axisLine: { onZero: false, lineStyle: { color: C.line } }, splitLine: { show: false } },
    yAxis: { type: "value", min: 0, max: 1, axisLabel: { color: C.text2, fontSize: 11, formatter: (v: number) => `${v * 100}%` },
             axisLine: { show: false }, axisTick: { show: false }, splitLine: { lineStyle: { color: C.line } } },
    series: [
      series("confirmed", C.prahari, -0.12), series("single node", C.series, 0.12),
      { name: "report (SIM)", type: "scatter", symbol: "diamond", symbolSize: 11,
        itemStyle: { color: "transparent", borderColor: C.text2, borderWidth: 1.5 },
        data: pts.filter((p) => p.ref !== undefined).map((p) => ({ value: [cats.indexOf(`${p.spacing} m`) - 0.32, p.ref], pt: { ...p, mean: p.ref! } })) },
    ],
  };
}

/** Energy per day (SPEC View 6, M41): one bar per sensor mode on a log axis, one series hue (each bar is named on the
 *  axis), with the clear-day harvest as a dashed reference and the cloudy-day range as a band (M42). */
function energyOption(rows: EnergyRow[], harvest: { clear: number; cloudy: [number, number] }): EOption {
  const lo = 0.05;
  const hi = 10 ** Math.ceil(Math.log10(Math.max(...rows.map((r) => r.wh), harvest.clear) * 1.5));
  return {
    animation: false,
    title: { text: "Energy per node per day (M41) against solar harvest (M42)", left: 4, top: 2,
             textStyle: { color: C.text, fontSize: 13, fontWeight: 500 } },
    grid: { left: 130, right: 150, top: 36, bottom: 40 },
    tooltip: { trigger: "item", ...tip, formatter: (p: { data: { row?: EnergyRow } }) => {
      const r = p.data.row;
      return r ? `${r.label}<br/><b>${r.wh.toFixed(3)}</b> Wh per day · ${r.days.toFixed(1)} days on a full store · SIM` : "";
    } },
    xAxis: { type: "log", min: lo, max: hi, ...axis("Wh per day (log scale)"),
             axisLabel: { color: C.text2, fontSize: 11, formatter: (v: number) => String(v) } },
    yAxis: { type: "category", data: rows.map((r) => r.label), inverse: true, boundaryGap: true,
             axisLabel: { color: C.text, fontSize: 12 }, axisTick: { show: false }, axisLine: { lineStyle: { color: C.line } } },
    series: [{
      // Lollipop, not bars: a log axis has no zero for a bar to start from. Stem from the axis minimum, dot at the value.
      type: "scatter", symbolSize: 12, z: 3, itemStyle: { color: C.series, borderColor: "#161b1f", borderWidth: 2 },
      data: rows.map((r) => ({ value: [r.wh, r.label], row: r })),
      label: { show: true, position: "right", distance: 8, color: C.text, fontSize: 11,
               formatter: (p: { data: { row: EnergyRow } }) =>
                 `${p.data.row.wh < 1 ? p.data.row.wh.toFixed(2) : p.data.row.wh.toFixed(1)} Wh · ${p.data.row.days.toFixed(1)} d` },
      markArea: { silent: true, itemStyle: { color: "rgba(168, 162, 154, 0.10)" },
                  label: { show: true, position: "insideTop", color: C.text2, fontSize: 10, formatter: "cloudy-day harvest" },
                  data: [[{ xAxis: harvest.cloudy[0] }, { xAxis: harvest.cloudy[1] }]] },
      markLine: { silent: true, symbol: "none", label: { show: false }, data: [
        ...rows.map((r) => [{ coord: [lo, r.label], lineStyle: { color: C.series, width: 4, cap: "round", type: "solid" } },
                            { coord: [r.wh, r.label] }]),
        { xAxis: harvest.clear, lineStyle: { color: C.text2, type: "dashed", width: 1.5 },
          label: { show: true, position: "start", color: C.text2, fontSize: 10, formatter: "clear-day harvest" } },   // top: the y axis is inverted
      ] },
    }],
  };
}

/** Phase 7 charts beneath the pipeline comparison; each shows the seeds and days it came from. */
export function ExperimentCharts({ summary }: { summary: Summary }) {
  const dial = useMemo(() => dialPoints(summary), [summary]);
  const sp = useMemo(() => spacingPoints(summary), [summary]);
  const en = useMemo(() => energyRows(summary), [summary]);
  const d = summary.days;
  const days = `${d.calibration} + ${d.tuning} + ${d.test} simulated days per seed`;
  return (
    <>
      {dial.length ? (
        <section data-testid="dial">
          <EChart option={dialOption(dial)} height={260} testId="chart-dial" />
          <p className="muted small">Each point re-tunes the node threshold h (M28) for another node-local false-candidate
            target and replays the same runs; the largest point is the design target of one per node per 30 days.</p>
          <p className="chart-foot">SIMULATION · P2 · seeds {summary.seeds.join(", ")} · {days}</p>
        </section>
      ) : null}
      {en.length && summary.energy ? (
        <section data-testid="energy">
          <EChart option={energyOption(en, summary.energy.harvest_wh_day)} height={80 + en.length * 44} testId="chart-energy" />
          <p className="muted small">Each point: sensor, microcontroller and radio (hourly heartbeats at SF7, {summary.energy.toa_ms} ms on
            air) at {summary.energy.voltage_v} V; the label adds how many days a full {summary.energy.store_wh} Wh supercapacitor
            store (M43) lasts with no sun. A node runs indefinitely while its point sits left of the harvest.</p>
          <p className="chart-foot">SIMULATION · M41–M43 · per simulated day · computed from configs/default.yaml (no random draws)</p>
        </section>
      ) : null}
      {summary.learning ? <LearningCharts learning={summary.learning} /> : null}
      {sp.length ? (
        <section data-testid="spacing">
          <EChart option={spacingOption(sp)} height={270} testId="chart-spacing" />
          <p className="chart-foot">SIMULATION · P2 · seeds {summary.spacing?.seeds.join(", ")} · {days} · 100 nodes per layout</p>
        </section>
      ) : null}
    </>
  );
}
