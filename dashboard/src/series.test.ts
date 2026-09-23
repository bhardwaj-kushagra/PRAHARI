import { describe, expect, it } from "vitest";
import { hazeBands, minuteLabel, nodeSeries, pickNodes, sharedRange, thin, weatherSeries } from "./series";
import type { Frame } from "./types";

const frame = (t: number, haze: number, reading: number[], T = 30): Frame => ({
  t, weather: { T, RH: 40, wind_ms: 1.5, wind_dir_deg: 250, rain_mm: 0, ffmc: 85 },
  prior: { odds: 1e-4, quorum: 2, day_type: "dry_busy" },
  nodes: { state: reading.map(() => 0), reading, residual: reading, p: reading.map(() => 0.5), cusum: reading.map(() => 0),
           health: reading.map(() => 1), soc: reading.map(() => 1) },
  cusum_h: 8.8, haze, fires: [], packets: [], events: [], alerts: [], health: {},
});

describe("series extraction", () => {
  const frames = [frame(0, 0, [1, 2]), frame(10, 0.5, [3, 4], 31), frame(20, 1, [5, 6]), frame(30, 0, [7, 8]),
                  frame(40, 0.2, [9, 10])];

  it("reads weather and node series in time order", () => {
    expect(weatherSeries(frames, "T").v).toEqual([30, 31, 30, 30, 30]);
    expect(nodeSeries(frames, 1)).toEqual({ t: [0, 10, 20, 30, 40], v: [2, 4, 6, 8, 10] });
  });

  it("finds haze bands, including one still open at the end", () => {
    expect(hazeBands(frames)).toEqual([[10, 30], [40, 40]]);
  });

  it("thins evenly and keeps the ends", () => {
    const s = { t: Array.from({ length: 1001 }, (_, i) => i), v: Array.from({ length: 1001 }, (_, i) => i * 2) };
    const out = thin(s, 11);
    expect(out.t).toEqual([0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]);
    expect(thin(s, 5000)).toBe(s);
  });

  it("picks eight nodes spread across the network and a shared padded range", () => {
    expect(pickNodes(100)).toEqual([0, 14, 28, 42, 57, 71, 85, 99]);
    expect(pickNodes(5)).toEqual([0, 1, 2, 3, 4]);
    expect(sharedRange([{ t: [0], v: [0] }, { t: [0], v: [10] }])).toEqual([-0.5, 10.5]);
    expect(sharedRange([{ t: [0], v: [-2.1] }, { t: [0], v: [5.3] }])).toEqual([-2.5, 6]);
  });

  it("labels simulated minutes by day and clock time", () => {
    expect(minuteLabel(0)).toBe("d1 00:00");
    expect(minuteLabel(1440 + 615)).toBe("d2 10:15");
  });
});
