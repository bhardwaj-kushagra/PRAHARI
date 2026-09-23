// LiveSource (SPEC §6.1, Phase 6): frames streamed from the engine server's WebSocket. The server sends exactly the
// lines of a recording (header, frames, traces, footer), so a live view is a RecordingSource over what has arrived.
import type { Footer, Frame, Header, Trace } from "../types";
import { SUPPORTED_SCHEMA } from "../types";
import type { FrameSource } from "./FrameSource";
import { RecordingSource } from "./RecordingSource";

export interface LiveBuffer { header: Header | null; frames: Frame[]; traces: Trace[]; footer: Footer | null; error: string | null }

export function emptyBuffer(): LiveBuffer {
  return { header: null, frames: [], traces: [], footer: null, error: null };
}

/** Apply one streamed line to the buffer (pure apart from appending). Returns false for lines it ignores. */
export function applyLine(buf: LiveBuffer, obj: Record<string, unknown>): boolean {
  if ("header" in obj) {
    const h = obj.header as Header;
    if (h.schema !== SUPPORTED_SCHEMA) { buf.error = `unsupported schema ${h.schema}`; return false; }
    buf.header = h;
  } else if ("error" in obj) buf.error = String(obj.error);
  else if ("trace" in obj) buf.traces.push(obj.trace as Trace);
  else if ("footer" in obj) buf.footer = obj.footer as Footer;
  else if ("t" in obj && buf.header) {
    const f = obj as unknown as Frame;
    if (buf.frames.length && f.t < buf.frames[buf.frames.length - 1].t) return false;
    buf.frames.push(f);
  } else return false;
  return true;
}

/** A FrameSource over the frames received so far. A new view is made on each update so views re-render. */
export class LiveView implements FrameSource {
  readonly kind = "live" as const;
  private readonly rec: RecordingSource;
  constructor(readonly name: string, buf: LiveBuffer) {
    this.rec = new RecordingSource(name, { header: buf.header!, frames: buf.frames.slice(), traces: buf.traces.slice(),
                                           footer: buf.footer });
  }
  get header() { return this.rec.header; }
  get footer() { return this.rec.footer; }
  get frameCount() { return this.rec.frameCount; }
  get span() { return this.rec.span; }
  frameAt(i: number) { return this.rec.frameAt(i); }
  indexAt(t: number) { return this.rec.indexAt(t); }
  trace(id: string) { return this.rec.trace(id); }
  eventMarks() { return this.rec.eventMarks(); }
}

export function wsUrl(server: string): string {
  return server.replace(/^http/, "ws").replace(/\/$/, "") + "/frames";
}

/** Connect to a running live run; `onUpdate` receives a fresh view at most every `throttleMs`. */
export function connectLive(server: string, onUpdate: (v: LiveView, buf: LiveBuffer) => void,
                            onClose: (buf: LiveBuffer) => void, throttleMs = 250): () => void {
  const buf = emptyBuffer();
  const ws = new WebSocket(wsUrl(server));
  let last = 0;
  let timer: ReturnType<typeof setTimeout> | null = null;
  const emit = () => {
    timer = null;
    last = performance.now();
    if (buf.header && buf.frames.length) onUpdate(new LiveView(`live: ${buf.header.scenario}`, buf), buf);
  };
  ws.onmessage = (ev) => {
    try { applyLine(buf, JSON.parse(String(ev.data))); } catch { return; }
    if (timer === null) timer = setTimeout(emit, Math.max(0, throttleMs - (performance.now() - last)));
  };
  ws.onerror = () => { buf.error = buf.error ?? "WebSocket error — is the server running?"; };
  ws.onclose = () => { if (timer !== null) { clearTimeout(timer); emit(); } onClose(buf); };
  return () => ws.close();
}
