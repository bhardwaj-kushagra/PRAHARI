import { describe, expect, it } from "vitest";
import { candidateMarks, floorSeries, hSeries, nodeField } from "./series";
import type { Frame } from "./types";

const frame = (t: number, cusum: number[], extra: Partial<Frame["nodes"]> = {}, events: Frame["events"] = [],
               h = 218.7): Frame => ({
  t, weather: { T: 30, RH: 40, wind_ms: 1.5, wind_dir_deg: 250, rain_mm: 0, ffmc: 85 },
  prior: { odds: 1e-4, quorum: 2, day_type: "dry_busy" },
  nodes: { state: cusum.map(() => 0), reading: cusum, residual: cusum, p: cusum.map(() => 0.5), cusum,
           health: cusum.map(() => 1), soc: cusum.map(() => 1), ...extra },
  cusum_h: h, fires: [], packets: [], events, alerts: [], health: {},
});

describe("node inspector series (Phase 5)", () => {
  const frames = [
    frame(0, [0, 1]),                                                         // an older frame: no baseline, no n_cal
    frame(10, [5, 2], { baseline: [0.1, 0.2], n_cal: [0, 0] }),
    frame(20, [230, 3], { baseline: [0.3, 0.4], n_cal: [239, 239] }, [{ type: "candidate", node: 0 }]),
    frame(30, [0, 4], { baseline: [0.5, 0.6], n_cal: [240, 240] }, [{ type: "candidate", node: 1 }], 226.6),
  ];

  it("skips frames without the field", () => {
    expect(nodeField(frames, "baseline", 1)).toEqual({ t: [10, 20, 30], v: [0.2, 0.4, 0.6] });
    expect(nodeField(frames, "cusum", 0).v).toEqual([0, 5, 230, 0]);
  });

  it("gives the M26 floor 1/(n+1), which falls as calibration grows", () => {
    expect(floorSeries(frames, 0)).toEqual({ t: [10, 20, 30], v: [1, 1 / 240, 1 / 241] });
  });

  it("tracks h and the node's own candidates", () => {
    expect(hSeries(frames).v).toEqual([218.7, 218.7, 218.7, 226.6]);
    expect(candidateMarks(frames, 0)).toEqual([[20, 230]]);
    expect(candidateMarks(frames, 1)).toEqual([[30, 4]]);
  });
});
