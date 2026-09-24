import { describe, expect, it } from "vitest";
import { gaugeArc, hasPhase8, packetOutcome, recentPackets } from "./comms";
import { energyRows, type Summary } from "./results";
import type { FrameSource } from "./sources/FrameSource";
import type { Frame } from "./types";

const frame = (t: number, packets: Frame["packets"], extra: Partial<Frame["nodes"]> = {}): Frame => ({
  t, weather: { T: 30, RH: 40, wind_ms: 1, wind_dir_deg: 270, rain_mm: 0, ffmc: 85 }, prior: { odds: 1e-4, quorum: 2, day_type: "dry_busy" },
  nodes: { state: [0, 0], reading: [0, 0], residual: [0, 0], p: [1, 1], cusum: [0, 0], health: [1, 1], soc: [1, 0.1], ...extra },
  cusum_h: 1, fires: [], packets, events: [], alerts: [], health: {},
});
const source = (frames: Frame[]) => ({
  frameAt: (i: number) => frames[i],
  indexAt: (t: number) => { let k = 0; frames.forEach((f, i) => { if (f.t <= t) k = i; }); return k; },
}) as unknown as FrameSource;

describe("Phase 8 map helpers", () => {
  it("collects recent packets with their own minute", () => {
    const s = source([frame(0, [{ from: 0, to: "g1", ok: true, sf: 7 }]),
                      frame(10, [{ from: 1, to: "g1", ok: false, sf: 7, t: 6 }, { from: 0, to: "g1", ok: true, sf: 7 }])]);
    const got = recentPackets(s, 10, 10);
    expect(got.map((p) => [p.from, p.at, p.age])).toEqual([[1, 6, 4], [0, 10, 0]]);   // minute 0 is out of the window
  });
  it("names packet outcomes", () => {
    expect(packetOutcome({ from: 0, to: null, ok: false, sf: null, queued: true })).toBe("queued");
    expect(packetOutcome({ from: 0, to: "g1", ok: false, sf: 7 })).toBe("lost");
    expect(packetOutcome({ from: 0, to: "g1", ok: true, sf: 7 })).toBe("delivered");
  });
  it("draws gauge arcs and detects Phase 8 recordings", () => {
    expect(gaugeArc(0.25, 10)).toBe("M0,-10A10,10 0 0 1 10.00,-0.00");
    expect(gaugeArc(0.75, 10).includes(" 0 1 1 ")).toBe(true);                          // large-arc flag past half
    expect(hasPhase8(frame(0, []))).toEqual({ comms: false, energy: false });
    expect(hasPhase8(frame(0, [], { queue: [0, 0], mode: [0, 1] }))).toEqual({ comms: true, energy: true });
  });
  it("orders energy rows from the lowest budget", () => {
    const s = { energy: { rows: [{ sensor: "MQ-2", mode: "heater on", wh_day: 22.9, autonomy_days: 0.2 },
                                 { sensor: "BME688", mode: "ULP", wh_day: 0.11, autonomy_days: 40 }] } } as unknown as Summary;
    expect(energyRows(s).map((r) => [r.label, r.y])).toEqual([["BME688 ULP", 0], ["MQ-2 heater on", 1]]);
  });
});
