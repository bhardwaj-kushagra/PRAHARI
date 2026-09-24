import { useEffect } from "react";
import { create } from "zustand";
import { variantName } from "../edge";
import { useMapView } from "../mapView";
import { keyAction, type Step, type Storyboard, stepMinute, storyboardProblems } from "../presenter";
import { RecordingSource } from "../sources/RecordingSource";
import { useSim } from "../store";

const BASE = import.meta.env.BASE_URL;

interface Presenter {
  board: Storyboard | null;
  step: Step | null;
  note: string | null;          // a one-off message (missing variant, load error)
  recordings: string[];
}
export const usePresenter = create<Presenter>(() => ({ board: null, step: null, note: null, recordings: [] }));

// One load per recording for the whole talk: jumping back to a step is instant.
const cache = new Map<string, Promise<RecordingSource>>();
function load(name: string): Promise<RecordingSource> {
  if (!cache.has(name)) {
    const p = RecordingSource.fromUrl(`${BASE}recordings/${name}`);
    p.catch(() => cache.delete(name));
    cache.set(name, p);
  }
  return cache.get(name)!;
}

/** SPEC §6.4 — apply a storyboard step: recording, bookmark, speed, layers, tab, then play or hold. */
async function goTo(step: Step) {
  const sim = useSim.getState();
  usePresenter.setState({ step, note: null });
  try {
    if (step.recording && sim.source?.name !== step.recording) {
      sim.setLoading(true);
      sim.setSource(await load(step.recording));
      sim.setLoading(false);
    }
  } catch (e) {
    sim.setError(e instanceof Error ? e.message : String(e));
    usePresenter.setState({ note: `could not open ${step.recording}` });
    return;
  }
  const s = useSim.getState();
  const t = stepMinute(step);
  if (s.playing) s.togglePlay();
  if (t !== null) s.seek(t);
  if (step.speed) s.setSpeed(step.speed);
  if (step.layers) useMapView.setState((m) => ({ layers: { ...m.layers, ...step.layers } }));
  s.selectNode(null);
  s.selectTrace(null);                                     // the Alerts tab then shows the latest alert
  if (step.panel) s.setPanel(step.panel);
  if (step.play) useSim.getState().togglePlay();
  if (step.scroll) {
    requestAnimationFrame(() => document.querySelector(`[data-testid="${step.scroll}"]`)
      ?.scrollIntoView({ block: "center", behavior: "smooth" }));
  }
}

/** S and R: open the pre-recorded variant with the mechanism flipped, keeping the clock (as the View 5 switches). */
async function flip(module: "scmr" | "raq") {
  const { source } = useSim.getState();
  if (!source || source.kind !== "recording") return;
  const to = source.header.modules[module] === "real" ? "stub" : "real";
  const name = variantName(source.name, module, to);
  if (!usePresenter.getState().recordings.includes(name)) {
    usePresenter.setState({ note: `no ${module.toUpperCase()} variant of this recording` });
    return;
  }
  const playing = useSim.getState().playing;
  useSim.getState().updateSource(await load(name));
  usePresenter.setState({ note: `${module.toUpperCase()} ${to === "real" ? "on" : "off"}` });
  if (playing && !useSim.getState().playing) useSim.getState().togglePlay();
}

function useStoryboard() {
  useEffect(() => {
    fetch(`${BASE}storyboard.json`).then((r) => (r.ok ? r.json() : null)).then((sb: Storyboard | null) => {
      if (!sb) return;
      const problems = storyboardProblems(sb);
      usePresenter.setState(problems.length ? { note: `storyboard.json: ${problems.join("; ")}` } : { board: sb });
      if (problems.length) console.warn("storyboard.json:", problems);
      // `?presenter` (the demo launchers' URL): open step 1 straight away.
      else if (new URLSearchParams(location.search).has("presenter")) void goTo(sb.steps.slice().sort((a, b) => a.key - b.key)[0]);
    }).catch(() => undefined);
    fetch(`${BASE}recordings/index.json`).then((r) => (r.ok ? r.json() : { recordings: [] }))
      .then((j: { recordings: string[] }) => usePresenter.setState({ recordings: j.recordings })).catch(() => undefined);
  }, []);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
      const a = keyAction(e);
      if (!a) return;
      const { board } = usePresenter.getState();
      if (a.kind === "step") {
        const step = board?.steps.find((s) => s.key === a.key);
        if (step) { e.preventDefault(); void goTo(step); }
      } else if (a.kind === "fullscreen") {
        if (document.fullscreenElement) void document.exitFullscreen();
        else void document.documentElement.requestFullscreen?.().catch(() => undefined);
      } else if (a.kind === "switch") {
        void flip(a.module);
      } else {
        usePresenter.setState({ step: null, note: null });
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
}

/** The caption strip over the map: the step, its line to say, and the keys. Hidden until a step key is pressed. */
export function PresenterOverlay() {
  useStoryboard();
  const board = usePresenter((s) => s.board);
  const step = usePresenter((s) => s.step);
  const note = usePresenter((s) => s.note);
  if (!step && !note) return null;
  return (
    <div className="presenter" data-testid="presenter" role="status" aria-live="polite">
      {step ? (
        <p className="presenter-line">
          <span className="presenter-step">{step.key}/{board?.steps.length ?? 9} · {step.title}</span>
          <span data-testid="presenter-caption">{step.caption}</span>
        </p>
      ) : null}
      {note ? <p className="presenter-note small" data-testid="presenter-note">{note}</p> : null}
      <p className="presenter-keys small muted">1–9 steps · Space play · S SCMR · R RAQ · F full screen · Esc hide · SIMULATION</p>
    </div>
  );
}
