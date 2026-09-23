import { gzipSync } from "node:zlib";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { decodeRecordingBytes, isGzip, parseRecording, RecordingError } from "./parseRecording";
import { RecordingSource } from "./RecordingSource";

const header = {
  schema: "prahari.frame/1", label: "SIMULATION", scenario: "t", description: "", seed: 11,
  start: "2026-04-15T00:00", days: 1, tick_minutes: 1, n_ticks: 20, record_every: 5,
  map: { width_m: 100, height_m: 100, interfaces: [] }, spacing_m: 70, radius_m: 112,
  nodes: [{ id: 0, x: 0, y: 0, type: "B" }], gateways: [], modules: { qcc: "stub" }, model_card: [],
};
const frame = (t: number, extra: object = {}) => ({
  t, weather: { T: 30, RH: 40, wind_ms: 1.5, wind_dir_deg: 270, rain_mm: 0, ffmc: 85 },
  prior: { odds: 1e-4, quorum: 2, day_type: "dry_busy" },
  nodes: { state: [0], reading: [0], residual: [0], p: [0.5], cusum: [0], health: [1], soc: [1] },
  cusum_h: 8.8, fires: [], packets: [], events: [], alerts: [], health: { qcc: "stub" }, ...extra,
});
const text = [
  JSON.stringify({ header }),
  JSON.stringify(frame(0)),
  JSON.stringify(frame(5, { events: [{ type: "candidate", node: 0, trace_id: "c-0-5" }] })),
  JSON.stringify({ trace: { trace_id: "c-0-5", t: 5, type: "candidate" } }),
  JSON.stringify(frame(10, { alerts: [{ level: "CONFIRMED", cluster: [0], trace_id: "c-0-5" }] })),
  JSON.stringify({ footer: { frames: 3, traces: 1, health: {} } }),
].join("\n") + "\n";

describe("parseRecording", () => {
  it("splits header, frames, traces and footer", () => {
    const r = parseRecording(text);
    expect(r.header.seed).toBe(11);
    expect(r.frames.map((f) => f.t)).toEqual([0, 5, 10]);
    expect(r.traces).toHaveLength(1);
    expect(r.footer?.frames).toBe(3);
  });
  it("rejects a missing header, an unknown schema and out-of-order frames", () => {
    expect(() => parseRecording(JSON.stringify(frame(0)))).toThrow(RecordingError);
    expect(() => parseRecording(JSON.stringify({ header: { ...header, schema: "x/9" } }))).toThrow(/unsupported schema/);
    const bad = [JSON.stringify({ header }), JSON.stringify(frame(5)), JSON.stringify(frame(0))].join("\n");
    expect(() => parseRecording(bad)).toThrow(/out of order/);
  });
});

describe("decodeRecordingBytes", () => {
  it("reads plain and gzipped bytes", async () => {
    const plain = new TextEncoder().encode(text);
    const gz = new Uint8Array(gzipSync(plain));
    expect(isGzip(plain)).toBe(false);
    expect(isGzip(gz)).toBe(true);
    expect(await decodeRecordingBytes(plain)).toBe(text);
    expect(await decodeRecordingBytes(gz)).toBe(text);
  });
});

describe("RecordingSource", () => {
  it("implements FrameSource lookups", async () => {
    const src = await RecordingSource.fromBytes("t.prs.jsonl", new TextEncoder().encode(text));
    expect(src.kind).toBe("recording");
    expect(src.span).toEqual([0, 10]);
    expect(src.indexAt(-3)).toBe(0);
    expect(src.indexAt(4)).toBe(0);
    expect(src.indexAt(5)).toBe(1);
    expect(src.indexAt(9.5)).toBe(1);
    expect(src.indexAt(99)).toBe(2);
    expect(src.trace("c-0-5")?.type).toBe("candidate");
    expect(src.eventMarks().map((m) => m.kind)).toEqual(["candidate", "alert"]);
  });

  it("opens the committed smoke recording produced by the engine", async () => {
    const bytes = new Uint8Array(readFileSync(join(__dirname, "..", "..", "..", "recordings", "smoke.prs.jsonl.gz")));
    const src = await RecordingSource.fromBytes("smoke.prs.jsonl.gz", bytes);
    expect(src.header.label).toBe("SIMULATION");
    expect(src.header.nodes).toHaveLength(100);
    expect(src.span[0]).toBe(0);
    expect(src.eventMarks().some((m) => m.kind === "ignition")).toBe(true);
  });
});
