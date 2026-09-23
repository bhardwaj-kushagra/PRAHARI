import { describe, expect, it } from "vitest";
import { baseName, logPos, runCounters, variantName, variantOf } from "./edge";
import { applyLine, emptyBuffer, wsUrl } from "./sources/LiveSource";
import type { Frame, NodeInfo } from "./types";

const nodes: NodeInfo[] = [{ id: 0, x: 0, y: 0, type: "B" }, { id: 1, x: 70, y: 0, type: "B" }, { id: 2, x: 1000, y: 1000, type: "B" }];
const frame = (t: number, events: Frame["events"] = [], alerts: Frame["alerts"] = []): Frame => ({
  t, weather: { T: 30, RH: 40, wind_ms: 1.5, wind_dir_deg: 250, rain_mm: 0, ffmc: 85 },
  prior: { odds: 1e-4, quorum: 2, day_type: "dry_busy" },
  nodes: { state: [0, 0, 0], reading: [0, 0, 0], residual: [0, 0, 0], p: [1, 1, 1], cusum: [0, 0, 0], health: [1, 1, 1],
           soc: [1, 1, 1] },
  cusum_h: 218.7, fires: [], packets: [], events, alerts, health: {},
});

describe("replay variants (mechanism switches)", () => {
  it("names and parses variant recordings", () => {
    expect(baseName("node_mature__scmr-stub.prs.jsonl.gz")).toBe("node_mature");
    expect(variantName("node_mature.prs.jsonl.gz", "scmr", "stub")).toBe("node_mature__scmr-stub.prs.jsonl.gz");
    expect(variantName("node_mature__scmr-stub.prs.jsonl.gz", "scmr", "real")).toBe("node_mature.prs.jsonl.gz");
    expect(variantOf("node_mature__scmr-stub.prs.jsonl.gz")).toEqual({ module: "scmr", state: "stub" });
    expect(variantOf("node_mature.prs.jsonl.gz")).toBeNull();
  });
});

describe("live counters (M46 rule)", () => {
  it("counts detections within 150 m and 3 h, and everything else as false", () => {
    const frames = [
      frame(0, [{ type: "ignition", x: 10, y: 0, fire: 0 }]),
      frame(40, [], [{ level: "CONFIRMED", cluster: [0, 1], trace_id: "d1" }]),
      frame(50, [], [{ level: "CONFIRMED", cluster: [2], trace_id: "d2" }]),
      frame(300, [], [{ level: "CONFIRMED", cluster: [0], trace_id: "d3" }]),     // too late for the fire
    ];
    expect(runCounters(frames, nodes, 3)).toEqual({ falseAlarms: 2, fires: 1, detected: 1, medianLatency: 40 });
    expect(runCounters(frames, nodes, 0)).toEqual({ falseAlarms: 0, fires: 1, detected: 0, medianLatency: null });
  });
  it("places values on a log scale", () => {
    expect(logPos(1e-2, 1e-4, 1)).toBeCloseTo(0.5);
    expect(logPos(0, 1e-4, 1)).toBe(0);
    expect(logPos(10, 1e-4, 1)).toBe(1);
  });
});

describe("live stream parsing", () => {
  it("applies recording lines in order and rejects out-of-order frames", () => {
    const buf = emptyBuffer();
    expect(applyLine(buf, { t: 0 })).toBe(false);                                  // no header yet
    expect(applyLine(buf, { header: { schema: "prahari.frame/1" } })).toBe(true);
    expect(applyLine(buf, frame(5) as unknown as Record<string, unknown>)).toBe(true);
    expect(applyLine(buf, frame(3) as unknown as Record<string, unknown>)).toBe(false);
    applyLine(buf, { trace: { trace_id: "c-1-5", t: 5, type: "candidate" } });
    applyLine(buf, { footer: { frames: 1 } });
    expect([buf.frames.length, buf.traces.length, buf.footer]).toEqual([1, 1, { frames: 1 }]);
    const bad = emptyBuffer();
    applyLine(bad, { header: { schema: "x/9" } });
    expect(bad.error).toMatch(/unsupported schema/);
    expect(wsUrl("http://localhost:8000/")).toBe("ws://localhost:8000/frames");
  });
});
