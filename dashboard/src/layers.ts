// Pure helpers for the map layers (Phase 1). Colour choices follow SPEC §6.3 and are
// validated with the dataviz ordinal check (one hue, monotone lightness, clears the dark surface).
import type { LayoutName } from "./types";

export const LAYOUT_NAMES: LayoutName[] = ["grid", "corridor", "greedy"];

/** Spreading factor is ordinal: one blue hue, dim (SF7, strongest link) → bright (SF12, weakest). */
export const SF_RAMP: Record<number, string> = {
  7: "#184f95", 8: "#256abf", 9: "#3987e5", 10: "#6da7ec", 11: "#9ec5f4", 12: "#cde2fb",
};
export const NO_LINK = "#7e8790";

export function sfColour(sf: number | null | undefined): string {
  return sf != null && SF_RAMP[sf] ? SF_RAMP[sf] : NO_LINK;
}

/** "One satellite pixel ≈ N node cells" (DER): N = (pixel / spacing)², rounded. */
export function pixelCaption(pixelM: number, spacingM: number): { cells: number; text: string } {
  const cells = Math.round((pixelM / spacingM) ** 2);
  return { cells, text: `one satellite pixel (${pixelM} m) ≈ ${cells} node cells at ${spacingM} m` };
}

/**
 * Relative ignition likelihood (0..1, row 0 = southern edge) → RGBA pixels for a canvas whose
 * row 0 is the northern edge. One hue (warm white) with alpha rising with likelihood.
 */
export function lambdaToRGBA(values: number[], nx: number, ny: number,
                             rgb: [number, number, number] = [232, 227, 218], maxAlpha = 0.5): Uint8ClampedArray<ArrayBuffer> {
  const out = new Uint8ClampedArray(nx * ny * 4);
  for (let row = 0; row < ny; row++) {
    const src = (ny - 1 - row) * nx;
    for (let col = 0; col < nx; col++) {
      const v = Math.max(0, Math.min(1, values[src + col] ?? 0));
      const o = (row * nx + col) * 4;
      out[o] = rgb[0]; out[o + 1] = rgb[1]; out[o + 2] = rgb[2];
      out[o + 3] = Math.round(255 * maxAlpha * v);
    }
  }
  return out;
}

/** Glyphs and labels were designed for a 700 m map; scale them with the map width. */
export function glyphScale(widthM: number): number {
  return Math.max(1, widthM / 700);
}

/** SVG points attribute with y flipped (north up). */
export function svgPoints(points: [number, number][], H: number): string {
  return points.map(([x, y]) => `${x},${H - y}`).join(" ");
}

export function pct(v: number | null | undefined): string {
  return v == null ? "—" : `${Math.round(v * 100)}%`;
}
