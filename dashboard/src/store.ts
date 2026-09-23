import { create } from "zustand";
import type { FrameSource } from "./sources/FrameSource";

export const SPEEDS = [1, 10, 60, 600] as const;   // ×real time (SPEC §6.2)
export type Panel = "health" | "node" | "alerts";

interface State {
  source: FrameSource | null;
  loading: boolean;
  error: string | null;
  simT: number;               // simulated minutes since start
  playing: boolean;
  speed: number;
  selectedNode: number | null;
  panel: Panel;
  setSource: (s: FrameSource) => void;
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
  setSource: (source) => set({ source, simT: source.span[0], playing: false, error: null, selectedNode: null }),
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

/** Current frame for the store's simulated time. */
export function useFrame() {
  const source = useSim((s) => s.source);
  const simT = useSim((s) => s.simT);
  if (!source) return null;
  return source.frameAt(source.indexAt(simT));
}
