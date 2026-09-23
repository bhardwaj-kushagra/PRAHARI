// Pure helpers for the map layers (Phase 1). Colour choices follow SPEC §6.3 and are
// validated with the dataviz ordinal check (one hue, monotone lightness, clears the dark surface).
import type { FrameSource } from "./sources/FrameSource";
import type { Frame, LayoutName, PlumeGrid } from "./types";

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

/** IEEE 754 half precision → number (the plume grid is stored as float16). */
export function halfToFloat(h: number): number {
  const s = h & 0x8000 ? -1 : 1;
  const e = (h >> 10) & 0x1f;
  const f = h & 0x3ff;
  if (e === 0) return s * 2 ** -14 * (f / 1024);
  if (e === 31) return f ? NaN : s * Infinity;
  return s * 2 ** (e - 15) * (1 + f / 1024);
}

/** Decode a plume grid's base64 float16 payload to a Float32Array (row 0 = south). */
export function decodePlume(g: PlumeGrid): Float32Array {
  const bin = atob(g.data);
  const out = new Float32Array(g.nx * g.ny);
  for (let i = 0; i < out.length; i++) out[i] = halfToFloat(bin.charCodeAt(2 * i) | (bin.charCodeAt(2 * i + 1) << 8));
  return out;
}

/** Smoke alpha on a log scale of su: 0 at `lo`, `maxAlpha` at `hi` and above (one cool slate hue). */
export const SMOKE_RGB: [number, number, number] = [159, 179, 200];
export function smokeAlpha(c: number, lo = 0.05, hi = 2.5, maxAlpha = 0.75): number {
  if (!(c > lo)) return 0;
  return maxAlpha * Math.min(1, Math.log(c / lo) / Math.log(hi / lo));
}

/** Plume values → RGBA pixels with north up. */
export function plumeToRGBA(values: Float32Array, nx: number, ny: number): Uint8ClampedArray<ArrayBuffer> {
  const out = new Uint8ClampedArray(nx * ny * 4);
  for (let row = 0; row < ny; row++) {
    const src = (ny - 1 - row) * nx;
    for (let col = 0; col < nx; col++) {
      const o = (row * nx + col) * 4;
      out[o] = SMOKE_RGB[0]; out[o + 1] = SMOKE_RGB[1]; out[o + 2] = SMOKE_RGB[2];
      out[o + 3] = Math.round(255 * smokeAlpha(values[src + col]));
    }
  }
  return out;
}

/** The newest plume grid at or before simulated time t, no older than `maxAgeMin`, while fires are burning. */
export function latestPlume(source: FrameSource, t: number, maxAgeMin: number): Frame | null {
  let i = source.indexAt(t);
  const now = source.frameAt(i);
  if (!now.fires.length) return null;
  for (; i >= 0; i--) {
    const f = source.frameAt(i);
    if (now.t - f.t > maxAgeMin) return null;
    if (f.plume) return f;
  }
  return null;
}

/** Node glow opacity from the fire signal at the node (su): full at 2.5 su (the 50 m design value). */
export function glowOpacity(conc: number | undefined): number {
  return conc && conc > 0.05 ? Math.min(1, conc / 2.5) * 0.8 : 0;
}
