import { SUPPORTED_SCHEMA, type Frame, type Recording, type Trace } from "../types";

export class RecordingError extends Error {}

/** Parse the text of a .prs.jsonl recording (SPEC §4.6). Pure: text in, Recording out. */
export function parseRecording(text: string): Recording {
  const lines = text.split("\n").filter((l) => l.trim().length > 0);
  if (lines.length === 0) throw new RecordingError("empty recording");
  let first: unknown;
  try {
    first = JSON.parse(lines[0]);
  } catch {
    throw new RecordingError("not a PRAHARI recording: line 1 is not JSON");
  }
  if (!first || typeof first !== "object" || !("header" in first)) {
    throw new RecordingError("not a PRAHARI recording: line 1 must be the header");
  }
  const header = (first as { header: Recording["header"] }).header;
  if (header.schema !== SUPPORTED_SCHEMA) {
    throw new RecordingError(`unsupported schema ${header.schema}; expected ${SUPPORTED_SCHEMA}`);
  }
  const frames: Frame[] = [];
  const traces: Trace[] = [];
  let footer: Recording["footer"] = null;
  for (let i = 1; i < lines.length; i++) {
    let obj: Record<string, unknown>;
    try {
      obj = JSON.parse(lines[i]);
    } catch {
      // Release 1.0: a final line cut off mid-write (an interrupted copy or run) is skipped, so the frames before it
      // still open; the missing footer marks the recording as incomplete. Any other bad line is still an error.
      if (i === lines.length - 1 && i > 1) {
        console.warn(`recording: last line ${i + 1} is incomplete and was skipped`);
        break;
      }
      throw new RecordingError(`line ${i + 1} is not JSON`);
    }
    if ("trace" in obj) traces.push(obj.trace as Trace);
    else if ("footer" in obj) footer = obj.footer as Recording["footer"];
    else if ("t" in obj) frames.push(obj as unknown as Frame);
    else throw new RecordingError(`line ${i + 1}: unknown record`);
  }
  if (frames.length === 0) throw new RecordingError("recording has no frames");
  for (let i = 1; i < frames.length; i++) {
    if (frames[i].t < frames[i - 1].t) throw new RecordingError(`frames out of order at line ${i + 2}`);
  }
  return { header, frames, traces, footer };
}

/** True when the bytes start with the gzip magic number. */
export function isGzip(bytes: Uint8Array): boolean {
  return bytes.length >= 2 && bytes[0] === 0x1f && bytes[1] === 0x8b;
}

/** Decode recording bytes, gunzipping with the platform DecompressionStream when needed (no library).
 *  Release 1.0 (second audit): a .gz file cut off in a copy is read up to where it breaks; the lines recovered open
 *  as an incomplete recording (see `parseRecording`). A file with nothing readable is a clear error. */
export async function decodeRecordingBytes(bytes: Uint8Array): Promise<string> {
  if (!isGzip(bytes)) return new TextDecoder().decode(bytes);
  const reader = new Blob([bytes as BlobPart]).stream().pipeThrough(new DecompressionStream("gzip")).getReader();
  const decoder = new TextDecoder();
  let text = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      text += decoder.decode(value, { stream: true });
    }
    return text + decoder.decode();
  } catch {
    if (!text.trim()) throw new RecordingError("the .gz file is damaged or incomplete: nothing could be decompressed");
    console.warn("recording: the .gz file ends early; the part that could be read is shown");
    return text + decoder.decode();
  }
}
