import type { Footer, Frame, Header, Recording, Trace } from "../types";
import type { FrameSource } from "./FrameSource";
import { decodeRecordingBytes, parseRecording } from "./parseRecording";

export class RecordingSource implements FrameSource {
  readonly kind = "recording" as const;
  readonly header: Header;
  readonly footer: Footer | null;
  private readonly frames: Frame[];
  private readonly times: number[];
  private readonly traces: Map<string, Trace>;

  constructor(readonly name: string, rec: Recording) {
    this.header = rec.header;
    this.footer = rec.footer;
    this.frames = rec.frames;
    this.times = rec.frames.map((f) => f.t);
    this.traces = new Map(rec.traces.map((t) => [t.trace_id, t]));
  }

  static async fromBytes(name: string, bytes: Uint8Array): Promise<RecordingSource> {
    return new RecordingSource(name, parseRecording(await decodeRecordingBytes(bytes)));
  }

  static async fromUrl(url: string): Promise<RecordingSource> {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`could not load ${url}: HTTP ${res.status}`);
    return RecordingSource.fromBytes(url.split("/").pop() ?? url, new Uint8Array(await res.arrayBuffer()));
  }

  static async fromFile(file: File): Promise<RecordingSource> {
    return RecordingSource.fromBytes(file.name, new Uint8Array(await file.arrayBuffer()));
  }

  get frameCount(): number {
    return this.frames.length;
  }

  get span(): [number, number] {
    return [this.times[0], this.times[this.times.length - 1]];
  }

  frameAt(index: number): Frame {
    return this.frames[Math.max(0, Math.min(index, this.frames.length - 1))];
  }

  indexAt(t: number): number {
    let lo = 0;
    let hi = this.times.length - 1;
    if (t <= this.times[0]) return 0;
    while (lo < hi) {
      const mid = (lo + hi + 1) >> 1;
      if (this.times[mid] <= t) lo = mid;
      else hi = mid - 1;
    }
    return lo;
  }

  trace(id: string): Trace | undefined {
    return this.traces.get(id);
  }

  eventMarks() {
    const out: ReturnType<FrameSource["eventMarks"]> = [];
    for (const f of this.frames) {
      for (const e of f.events) {
        if (e.type === "ignition") out.push({ t: f.t, kind: "ignition" });
        else if (e.type === "candidate") out.push({ t: f.t, kind: "candidate" });
        else if (e.type === "satellite_alert") out.push({ t: f.t, kind: "satellite" });
        else if (e.type === "degraded") out.push({ t: f.t, kind: "degraded" });
      }
      if (f.alerts.length) out.push({ t: f.t, kind: "alert" });
    }
    return out;
  }
}
