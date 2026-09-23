import { useMemo } from "react";
import { daysLabel } from "../format";
import { hazeBands, hazeSeries, minuteLabel, nodeSeries, pickNodes, type Series, sharedRange, thin,
         weatherSeries } from "../series";
import { useSim } from "../store";
import type { Frame } from "../types";
import { EChart, type EOption } from "./EChart";

// Colours: text tokens for text (SPEC §6.3); one neutral series hue (dataviz slot 1, dark step);
// ember, amber and pine stay reserved for node states on the map.
const C = { text: "#e8e3da", text2: "#a8a29a", line: "#2a3238", series: "#3987e5", band: "rgba(168,162,154,0.16)" };

interface LineSpec {
  title: string; unit: string; s: Series; cursor: number; bands?: [number, number][];
  yRange?: [number, number]; compact?: boolean; span: [number, number];
}

/** One single-series line chart: title names the series (no legend), recessive axes, hover tooltip, time cursor. */
function lineOption({ title, unit, s, cursor, bands = [], yRange, compact = false, span }: LineSpec): EOption {
  return {
    animation: false,
    title: { text: title, left: 4, top: 2, textStyle: { color: C.text, fontSize: compact ? 12 : 13, fontWeight: 500,
                                                          fontFamily: "IBM Plex Sans" } },
    grid: { left: compact ? 36 : 46, right: 10, top: compact ? 24 : 28, bottom: compact ? 18 : 24 },
    tooltip: {
      trigger: "axis", backgroundColor: "#161b1f", borderColor: C.line, textStyle: { color: C.text, fontSize: 12 },
      formatter: (ps: { value: [number, number] }[]) => {
        const [t, v] = ps[0].value;
        return `${minuteLabel(t)}<br/><b>${Number(v).toPrecision(4)}</b> ${unit} · SIM`;
      },
    },
    xAxis: {
      type: "value", min: span[0], max: span[1], splitNumber: compact ? 3 : 6,
      axisLabel: { color: C.text2, fontSize: 11, formatter: (v: number) => minuteLabel(v).replace(":00", "h") },
      axisLine: { lineStyle: { color: C.line } }, splitLine: { show: false },
    },
    yAxis: {
      type: "value", scale: true, min: yRange?.[0], max: yRange?.[1], splitNumber: compact ? 2 : 3,
      axisLabel: { color: C.text2, fontSize: 11, formatter: (v: number) => Number(v.toPrecision(3)).toString() },
      splitLine: { lineStyle: { color: C.line } },
    },
    series: [{
      type: "line", showSymbol: false, data: s.t.map((t, i) => [t, s.v[i]]),
      lineStyle: { width: compact ? 1.5 : 2, color: C.series }, itemStyle: { color: C.series },
      markLine: { silent: true, symbol: "none", label: { show: false }, lineStyle: { color: C.text, width: 1, type: "solid" },
                  data: [{ xAxis: cursor }] },
      markArea: bands.length ? { silent: true, itemStyle: { color: C.band },
                                 label: { show: !compact, color: C.text2, fontSize: 11, position: "insideTop" },
                                 data: bands.map(([a, b]) => [{ xAxis: a, name: "haze" }, { xAxis: b }]) } : undefined,
    }],
  };
}

function useFrames(): Frame[] {
  const source = useSim((s) => s.source);
  return useMemo(() => {
    if (!source) return [];
    return Array.from({ length: source.frameCount }, (_, i) => source.frameAt(i));
  }, [source]);
}

/** Phase 2 views: weather strip, node inspector (reading) and eight-node small multiples. */
export function SignalsPanel() {
  const source = useSim((s) => s.source);
  const selected = useSim((s) => s.selectedNode);
  const frames = useFrames();
  const span: [number, number] = source ? source.span : [0, 1];
  const step = Math.max(5, (span[1] - span[0]) / 400);                   // cursor granularity keeps redraws cheap
  const cursor = useSim((s) => Math.floor(s.simT / step) * step);
  const bands = useMemo(() => hazeBands(frames), [frames]);
  const weather = useMemo(() => ({
    T: thin(weatherSeries(frames, "T")), RH: thin(weatherSeries(frames, "RH")),
    wind: thin(weatherSeries(frames, "wind_ms")), ffmc: thin(weatherSeries(frames, "ffmc")),
    haze: thin(hazeSeries(frames)),
  }), [frames]);
  const n = source?.header.nodes.length ?? 0;
  const picks = useMemo(() => pickNodes(n), [n]);
  const multi = useMemo(() => picks.map((i) => thin(nodeSeries(frames, i), 600)), [frames, picks]);
  const range = useMemo(() => sharedRange(multi), [multi]);
  const inspected = selected ?? picks[0] ?? 0;
  const insp = useMemo(() => thin(nodeSeries(frames, inspected)), [frames, inspected]);

  const opts = useMemo(() => ({
    T: lineOption({ title: "Air temperature · °C (M5)", unit: "°C", s: weather.T, cursor, compact: true, span }),
    RH: lineOption({ title: "Relative humidity · % (M6)", unit: "%", s: weather.RH, cursor, compact: true, span }),
    wind: lineOption({ title: "Wind at 10 m · m/s (M5)", unit: "m/s", s: weather.wind, cursor, compact: true, span }),
    ffmc: lineOption({ title: "FFMC · daily at noon (M7)", unit: "", s: weather.ffmc, cursor, compact: true, span }),
    haze: lineOption({ title: "Regional haze H(t) · su (M20)", unit: "su", s: weather.haze, cursor, compact: true, span }),
    insp: lineOption({ title: `Node ${inspected} · sensor reading · su (M18)`, unit: "su", s: insp, cursor, bands, span }),
    multi: multi.map((s, k) => lineOption({ title: `node ${picks[k]}`, unit: "su", s, cursor, bands, yRange: range,
                                             compact: true, span })),
  }), [weather, insp, multi, picks, range, bands, cursor, inspected, span[0], span[1]]);

  if (!source || frames.length === 0) return null;
  const h = source.header;
  return (
    <div className="signals" data-testid="signals">
      <h2>Weather and fuel moisture</h2>
      <div className="mini-grid">
        <EChart option={opts.T} height={120} testId="chart-T" />
        <EChart option={opts.RH} height={120} />
        <EChart option={opts.wind} height={120} />
        <EChart option={opts.ffmc} height={120} />
      </div>
      <EChart option={opts.haze} height={110} />
      <h2>Node inspector</h2>
      <EChart option={opts.insp} height={190} testId="chart-inspector" />
      <p className="muted small">Click a node on the map, or a panel below, to inspect it. Shaded bands: haze episodes.</p>
      <h2>Eight nodes <span className="muted small">(shared scales)</span></h2>
      <div className="multi-grid">
        {opts.multi.map((o, k) => (
          <EChart key={picks[k]} option={o} height={96} testId={`multiple-${picks[k]}`}
                  onClick={() => useSim.setState({ selectedNode: picks[k] })} />
        ))}
      </div>
      <p className="chart-foot">
        SIMULATION · seed {h.seed} · {daysLabel(h.days)} · every {h.record_every}th tick plus event ticks · all values SIM
      </p>
    </div>
  );
}
