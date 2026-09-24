/** Phase 10 — presenter mode (SPEC §6.4): the storyboard of §11 as data, and the keys that drive it.
 *
 *  The storyboard lives in `public/storyboard.json`, so captions and bookmarks can be edited without rebuilding.
 *  Pure helpers only; the component `PresenterOverlay.tsx` applies a step to the stores. */
import type { LayerKey } from "./mapView";
import type { Panel } from "./store";

export interface Step {
  key: number;                  // 1–9
  title: string;
  recording?: string;           // file in public/recordings/; omitted = keep the open recording
  day?: number;                 // bookmark: simulated day (1-based) and local time "HH:MM" …
  time?: string;
  t?: number;                   // … or minutes since the start of the run
  speed?: number;               // ×real time
  play?: boolean;               // start playing on arrival
  panel?: Panel;                // tab to open
  layers?: Partial<Record<LayerKey, boolean>>;
  scroll?: string;              // data-testid to bring into view (e.g. the race timeline)
  seconds: number;              // planned speaking time (the rehearsal budget, acceptance 2)
  caption: string;              // the line to say, shown on screen
}
export interface Storyboard { title: string; steps: Step[] }

const PANELS: Panel[] = ["health", "signals", "node", "alerts", "results"];

/** Minutes since the start of the run for a step's bookmark; null = the recording's first frame. */
export function stepMinute(s: Step): number | null {
  if (typeof s.t === "number") return s.t;
  if (s.day === undefined) return null;
  const [h, m] = (s.time ?? "00:00").split(":").map(Number);
  return (s.day - 1) * 1440 + h * 60 + m;
}

/** Check a storyboard read from JSON; returns the problems found (empty when it is usable). */
export function storyboardProblems(sb: Storyboard): string[] {
  const out: string[] = [];
  if (!Array.isArray(sb?.steps) || !sb.steps.length) return ["no steps"];
  const keys = new Set<number>();
  for (const s of sb.steps) {
    if (!Number.isInteger(s.key) || s.key < 1 || s.key > 9) out.push(`step "${s.title}": key must be 1–9`);
    else if (keys.has(s.key)) out.push(`key ${s.key} used twice`);
    keys.add(s.key);
    if (s.panel && !PANELS.includes(s.panel)) out.push(`step ${s.key}: unknown panel "${s.panel}"`);
    if (s.time !== undefined && !/^\d{1,2}:\d{2}$/.test(s.time)) out.push(`step ${s.key}: time must be HH:MM`);
    if (!(s.seconds > 0)) out.push(`step ${s.key}: seconds must be positive`);
  }
  if (!sb.steps.some((s) => s.recording)) out.push("no step names a recording");
  return out;
}

/** Planned length of a full run-through in seconds (SPEC Phase 10 acceptance 2: ≤ 180). */
export function rehearsalSeconds(sb: Storyboard): number {
  return sb.steps.reduce((a, s) => a + s.seconds, 0);
}

export type KeyAction =
  | { kind: "step"; key: number }
  | { kind: "fullscreen" }
  | { kind: "switch"; module: "scmr" | "raq" }
  | { kind: "clear" };

/** SPEC §6.4 keys: 1–9 storyboard steps, F full screen, S SCMR, R RAQ (replay variants); Escape hides the caption.
 *  Space (play/pause) is handled by the app's own key handler. Modifier combinations are left to the browser. */
export function keyAction(e: { key: string; ctrlKey?: boolean; metaKey?: boolean; altKey?: boolean }): KeyAction | null {
  if (e.ctrlKey || e.metaKey || e.altKey) return null;
  if (/^[1-9]$/.test(e.key)) return { kind: "step", key: Number(e.key) };
  const k = e.key.toLowerCase();
  if (k === "f") return { kind: "fullscreen" };
  if (k === "s") return { kind: "switch", module: "scmr" };
  if (k === "r") return { kind: "switch", module: "raq" };
  if (e.key === "Escape") return { kind: "clear" };
  return null;
}
