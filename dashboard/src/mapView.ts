import { create } from "zustand";
import type { LayoutName } from "./types";

export type LayerKey = "interfaces" | "likelihood" | "smoke" | "baselines" | "links" | "coverage" | "satellite" | "packets" | "energy";

interface MapView {
  layers: Record<LayerKey, boolean>;
  preview: LayoutName | null;          // another layout shown for comparison; null = the simulated one
  toggleLayer: (k: LayerKey) => void;
  setPreview: (l: LayoutName | null) => void;
}

/** Map display state, separate from playback state. */
export const useMapView = create<MapView>((set) => ({
  layers: { interfaces: true, likelihood: true, smoke: true, baselines: true, links: false, coverage: false, satellite: false,
            packets: true, energy: true },
  preview: null,
  toggleLayer: (k) => set((s) => ({ layers: { ...s.layers, [k]: !s.layers[k] } })),
  setPreview: (preview) => set({ preview }),
}));
