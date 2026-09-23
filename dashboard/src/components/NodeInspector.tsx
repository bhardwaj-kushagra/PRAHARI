import { useMemo } from "react";
import { daysLabel } from "../format";
import { candidateMarks, floorSeries, hSeries, minuteLabel, nodeField, type Series, thin } from "../series";
import { useSim } from "../store";
import type { Frame } from "../types";
import { EChart, type EOption } from "./EChart";

// One validated series hue (dataviz slot 1, dark step); reference lines (baseline, floor, h) are neutral dashed text-2
// with an end label; candidate markers wear the reserved node-state ember of the map legend, labelled "candidate".
const C = { text: "#e8e3da", text2: "#a8a29a", line: "#2a3238", series: "#3987e5", ember: "#f26a2e" };

interface Line { name: string; s: Series; ref?: boolean; endLabel?: string }
interface StackSpec {
  title: string; unit: string; lines: Line[]; span: [number, number]; cursor: number; log?: boolean;
  marks?: [number, number][]; height?: "full" | "compact";
}

/** One panel of the stack: shared x span and cursor, one y-axis, crosshair tooltip, legend when > 1 series. */
function stackOption({ title, unit, lines, span, cursor, log = false, marks = [], height = "full" }: StackSpec): EOption {
  const compact = height === "compact";
  const names = [...lines.map((l) => l.name), ...(marks.length ? ["candidate"] : [])];
  const fmt = (v: number) => (log ? v.toExponential(1) : Number(v.toPrecision(3)).toString());
  return {
    animation: false,
    title: { text: title, left: 4, top: 2, textStyle: { color: C.text, fontSize: compact ? 12 : 13, fontWeight: 500 } },
    legend: names.length > 1 ? { top: 2, right: 8, textStyle: { color: C.text2, fontSize: 11 }, itemWidth: 14, itemHeight: 8,
                                 data: names } : undefined,
    grid: { left: 52, right: 64, top: compact ? 24 : 30, bottom: compact ? 18 : 24 },
    tooltip: {
      trigger: "axis", axisPointer: { type: "line", lineStyle: { color: C.text2 } },
      backgroundColor: "#161b1f", borderColor: C.line, textStyle: { color: C.text, fontSize: 12 },
      formatter: (ps: { seriesName: string; value: [number, number] }[]) =>
        `${minuteLabel(ps[0].value[0])}<br/>` +
        ps.map((p) => `${p.seriesName}: <b>${log ? Number(p.value[1]).toExponential(2) : Number(p.value[1]).toPrecision(4)}</b> ${unit}`)
          .join("<br/>") + " · SIM",
    },
    xAxis: {
      type: "value", min: span[0], max: span[1], splitNumber: 6,
      axisLabel: { color: C.text2, fontSize: 11, showMaxLabel: false, formatter: (v: number) => minuteLabel(v).replace(":00", "h") },
      axisLine: { lineStyle: { color: C.line } }, splitLine: { show: false },
    },
    yAxis: {
      type: log ? "log" : "value", scale: !log, splitNumber: compact ? 2 : 3,
      axisLabel: { color: C.text2, fontSize: 11, formatter: fmt }, splitLine: { lineStyle: { color: C.line } },
    },
    series: [
      ...lines.map((l, k) => ({
        name: l.name, type: "line", showSymbol: false, step: l.ref ? "end" : undefined, z: l.ref ? 2 : 3,
        data: l.s.t.map((t, i) => [t, l.s.v[i]]),
        lineStyle: l.ref ? { width: 1.5, color: C.text2, type: "dashed" } : { width: 2, color: C.series },
        itemStyle: { color: l.ref ? C.text2 : C.series },
        endLabel: l.endLabel ? { show: true, color: C.text2, fontSize: 11, formatter: l.endLabel } : undefined,
        markLine: k === 0 ? { silent: true, symbol: "none", label: { show: false },
                              lineStyle: { color: C.text, width: 1, type: "solid" }, data: [{ xAxis: cursor }] } : undefined,
      })),
      ...(marks.length ? [{ name: "candidate", type: "scatter", symbol: "circle", symbolSize: 9, z: 4, data: marks,
                            itemStyle: { color: C.ember, borderColor: "#161b1f", borderWidth: 2 } }] : []),
    ],
  };
}

function useFrames(): Frame[] {
  const source = useSim((s) => s.source);
  return useMemo(() => (source ? Array.from({ length: source.frameCount }, (_, i) => source.frameAt(i)) : []), [source]);
}

/** SPEC §6.2 View 2 — stacked, time-aligned node evidence: reading and slow baseline (M24), fast residual (M25),
 *  QCC p-value with its floor (M26), CUSUM with its threshold and candidates (M28), health weight (M29 stub). */
export function NodeInspector() {
  const source = useSim((s) => s.source);
  const node = useSim((s) => s.selectedNode);
  const frames = useFrames();
  const span: [number, number] = source ? source.span : [0, 1];
  const step = Math.max(5, (span[1] - span[0]) / 400);
  const cursor = useSim((s) => Math.floor(s.simT / step) * step);
  const data = useMemo(() => {
    if (node === null) return null;
    return {
      reading: thin(nodeField(frames, "reading", node)), baseline: thin(nodeField(frames, "baseline", node)),
      residual: thin(nodeField(frames, "residual", node)), p: thin(nodeField(frames, "p", node)),
      floor: thin(floorSeries(frames, node)), G: thin(nodeField(frames, "cusum", node)), h: thin(hSeries(frames)),
      health: thin(nodeField(frames, "health", node)), marks: candidateMarks(frames, node),
      soc: frames[0]?.nodes.mode ? thin(nodeField(frames, "soc", node)) : null,
    };
  }, [frames, node]);
  const opts = useMemo(() => {
    if (!data) return null;
    const hasB = data.baseline.t.length > 0;
    const hasF = data.floor.t.length > 0;
    return {
      reading: stackOption({ title: "Reading and slow baseline · su (M18, M24)", unit: "su", span, cursor,
                             lines: [{ name: "reading", s: data.reading },
                                     ...(hasB ? [{ name: "slow baseline b", s: data.baseline, ref: true }] : [])] }),
      residual: stackOption({ title: "Detection residual · su (M25 fast residual)", unit: "su", span, cursor,
                              lines: [{ name: "residual", s: data.residual }] }),
      p: stackOption({ title: "QCC p-value · log scale (M26)", unit: "", span, cursor, log: true,
                       lines: [{ name: "p-value", s: data.p },
                               ...(hasF ? [{ name: "floor 1/(n+1)", s: data.floor, ref: true, endLabel: "floor" }] : [])] }),
      G: stackOption({ title: "Node CUSUM G and threshold h (M28)", unit: "", span, cursor, marks: data.marks,
                       lines: [{ name: "G", s: data.G }, { name: "h", s: data.h, ref: true, endLabel: "h" }] }),
      health: stackOption({ title: "Health weight c (M29; stub = 1)", unit: "", span, cursor, height: "compact",
                            lines: [{ name: "c", s: data.health }] }),
      soc: data.soc ? stackOption({ title: "Stored energy · state of charge (M43)", unit: "", span, cursor, height: "compact",
                                    lines: [{ name: "state of charge", s: data.soc },
                                            { name: "ULP below", s: { t: [span[0], span[1]], v: [0.2, 0.2] }, ref: true, endLabel: "ULP" },
                                            { name: "stop below", s: { t: [span[0], span[1]], v: [0.05, 0.05] }, ref: true, endLabel: "stop" }] })
                  : null,
    };
  }, [data, cursor, span[0], span[1]]);

  if (!source || node === null || !opts || !data) return null;
  const h = source.header;
  return (
    <div className="inspector" data-testid="node-inspector">
      <h2>Node evidence <span className="muted small">{data.marks.length} candidate{data.marks.length === 1 ? "" : "s"} in this recording</span></h2>
      <EChart option={opts.reading} height={150} testId="chart-node-reading" />
      <EChart option={opts.residual} height={130} />
      <EChart option={opts.p} height={150} testId="chart-node-p" />
      <EChart option={opts.G} height={150} testId="chart-node-cusum" />
      <EChart option={opts.health} height={90} />
      {opts.soc ? <EChart option={opts.soc} height={110} testId="chart-node-soc" /> : null}
      <p className="chart-foot">
        SIMULATION · seed {h.seed} · {daysLabel(h.days, h.record_from_min)} · every {h.record_every}th tick plus event ticks · the floor
        steps with each 4-hour calibration bin · all values SIM
      </p>
    </div>
  );
}
