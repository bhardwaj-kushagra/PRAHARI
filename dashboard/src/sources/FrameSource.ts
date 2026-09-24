import type { Footer, Frame, Header, Trace } from "../types";

/**
 * The only interface views consume (SPEC §6.1). RecordingSource (Phase 0) replays files;
 * LiveSource (Phase 6) will stream from the engine server.
 */
export interface FrameSource {
  readonly kind: "recording" | "live";
  readonly name: string;
  readonly header: Header;
  readonly footer: Footer | null;
  readonly frameCount: number;
  /** Simulated minutes covered: [first frame t, last frame t]. */
  readonly span: [number, number];
  frameAt(index: number): Frame;
  /** Index of the last frame with t <= the given time (0 if none). */
  indexAt(t: number): number;
  trace(id: string): Trace | undefined;
  /** Ticks that carry events or alerts, for scrub-bar markers. */
  eventMarks(): { t: number; kind: "ignition" | "candidate" | "alert" | "satellite" | "degraded" }[];
}
