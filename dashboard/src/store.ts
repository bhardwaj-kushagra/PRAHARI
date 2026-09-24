import { create } from "zustand";
import type { FrameSource } from "./sources/FrameSource";

export const SPEEDS = [1, 10, 60, 600] as const;   // ×real time (SPEC §6.2)
export type Panel = "health" | "node" | "alerts" | "signals" | "results";

interface State {
  source: FrameSource | null;
  loading: boolean;
  error: string | null;
  simT: number;               // simulated minutes since start
  playing: boolean;
  speed: number;
  selectedNode: number | null;
  panel: Panel;
  selectedTrace: string | null;   // Phase 6: the alert whose evidence the "why" panel shows
  setSource: (s: FrameSource) => void;
  updateSource: (s: FrameSource) => void;
  selectTrace: (id: string | null) => void;
  setLoading: (b: boolean) => void;
  setError: (e: string | null) => void;
  togglePlay: () => void;
  setSpeed: (s: number) => void;
  seek: (t: number) => void;
  advance: (realSeconds: number) => void;
  stepFrame: (dir: 1 | -1) => void;
  selectNode: (i: number | null) => void;
  setPanel: (p: Panel) => void;
}

export const useSim = create<State>((set, get) => ({
  source: null,
  loading: false,
  error: null,
  simT: 0,
  playing: false,
  speed: 60,
  selectedNode: null,
  panel: "health",
  selectedTrace: null,
  setSource: (source) => set({ source, simT: source.span[0], playing: false, error: null, selectedNode: null,
                               selectedTrace: null }),
  // Live mode and replay variants: swap the source but keep the clock; at the live edge, follow new frames.
  updateSource: (source) => {
    const { source: old, simT, playing } = get();
    const atEdge = !old || simT >= old.span[1] - 1e-6;
    const t = atEdge && !playing ? source.span[1] : Math.max(source.span[0], Math.min(simT, source.span[1]));
    set({ source, simT: t, error: null });
  },
  selectTrace: (selectedTrace) => set({ selectedTrace }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error, loading: false }),
  togglePlay: () => {
    const { source, simT, playing } = get();
    if (!source) return;
    // Restart from the beginning when play is pressed at the end.
    if (!playing && simT >= source.span[1]) set({ simT: source.span[0] });
    set({ playing: !playing });
  },
  setSpeed: (speed) => set({ speed }),
  seek: (t) => {
    const { source } = get();
    if (!source) return;
    set({ simT: Math.max(source.span[0], Math.min(t, source.span[1])) });
  },
  advance: (realSeconds) => {
    const { source, simT, speed } = get();
    if (!source) return;
    const next = simT + (realSeconds * speed) / 60;   // ×60 = one simulated minute per second
    if (next >= source.span[1]) set({ simT: source.span[1], playing: false });
    else set({ simT: next });
  },
  stepFrame: (dir) => {
    const { source, simT } = get();
    if (!source) return;
    const i = source.indexAt(simT) + dir;
    set({ simT: source.frameAt(i).t, playing: false });
  },
  selectNode: (selectedNode) => set(selectedNode === null ? { selectedNode } : { selectedNode, panel: "node" }),
  setPanel: (panel) => set({ panel }),
}));

// Release 1.0 (second audit): every source load takes a token, and only the latest request may set the source.
// A slow load (presenter key, recording picker, mechanism switch, live stream) can never overwrite a newer choice.
let loadSeq = 0;
/** Start a source load; returns its token. */
export function beginLoad(): number { return ++loadSeq; }
/** True while no newer load has started since the one holding `token`. */
export function isLatestLoad(token: number): boolean { return token === loadSeq; }

/** Current frame for the store's simulated time. */
export function useFrame() {
  const source = useSim((s) => s.source);
  const simT = useSim((s) => s.simT);
  if (!source) return null;
  return source.frameAt(source.indexAt(simT));
}
