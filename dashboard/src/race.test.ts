import { describe, expect, it } from "vitest";
import { fireIds, fmtMin, raceDeltas, raceFor } from "./race";
import type { FrameSource } from "./sources/FrameSource";
import type { Frame, FrameEvent } from "./types";

const frame = (t: number, events: FrameEvent[] = [], alerts: Frame["alerts"] = []): Frame => ({
  t, weather: { T: 30, RH: 40, wind_ms: 1, wind_dir_deg: 270, rain_mm: 0, ffmc: 85 }, prior: { odds: 1e-4, quorum: 2, day_type: "dry_busy" },
  nodes: { state: [0, 0], reading: [0, 0], residual: [0, 0], p: [1, 1], cusum: [0, 0], health: [1, 1], soc: [1, 1] },
  cusum_h: 1, fires: [], packets: [], events, alerts, health: {},
});
const source = (frames: Frame[]) => ({
  header: { nodes: [{ id: 0, x: 50, y: 0 }, { id: 1, x: 900, y: 900 }] }, frameCount: frames.length,
  frameAt: (i: number) => frames[i],
}) as unknown as FrameSource;

describe("race timeline (acceptance 1: correct deltas on a scripted fire)", () => {
  const s = source([
    frame(840, [{ type: "ignition", fire: 0, x: 0, y: 0 },
                { type: "satellite_plan", fire: 0, overpass_t: 1350, platform: "Terra", alert_t: 1399.6, missed: [] }]),
    frame(870, [{ type: "candidate", node: 1 }]),                               // far from the fire: not counted
    frame(895, [{ type: "candidate", node: 0 }]),
    frame(921, [], [{ level: "CONFIRMED", cluster: [0], trace_id: "d" }]),
  ]);
  it("finds each marker", () => {
    const r = raceFor(s, 0)!;
    expect([r.ignition, r.candidate, r.confirmed, r.overpass, r.satellite]).toEqual([840, 895, 921, 1350, 1400]);   // alert rounded to its minute
    expect(fireIds(s)).toEqual([0]);
  });
  it("labels the deltas", () => {
    const d = raceDeltas(raceFor(s, 0)!);
    expect([d.toCandidate, d.toConfirm, d.toSatellite, d.lead]).toEqual([55, 81, 560, 479]);
    expect(d.headline).toBe("PRAHARI confirmed 7 h 59 min before the satellite alert");
  });
  it("says so when the satellite wins or nobody confirms", () => {
    const late = source([frame(0, [{ type: "ignition", fire: 3, x: 0, y: 0 },
                                  { type: "satellite_plan", fire: 3, overpass_t: 60, platform: "Aqua", alert_t: 100, missed: [] }]),
                         frame(130, [], [{ level: "CONFIRMED", cluster: [0], trace_id: "d" }])]);
    expect(raceDeltas(raceFor(late, 3)!).headline).toBe("The satellite alert came 30 min before PRAHARI confirmed");
    const none = source([frame(0, [{ type: "ignition", fire: 4, x: 0, y: 0 }])]);
    expect(raceDeltas(raceFor(none, 4)!).headline).toBe("PRAHARI did not confirm this fire in the recording");
    expect(fmtMin(125)).toBe("2 h 05 min");
  });
});
