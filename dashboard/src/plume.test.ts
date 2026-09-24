import { describe, expect, it } from "vitest";
import { decodePlume, glowOpacity, halfToFloat, latestPlume, plumeToRGBA, smokeAlpha } from "./layers";
import type { FrameSource } from "./sources/FrameSource";
import type { Frame } from "./types";

function f16base64(values: number[]): string {
  // Test-side encoder via DataView (matches numpy astype('<f2') for exactly representable values).
  const known: Record<number, number> = { 0: 0x0000, 1: 0x3c00, 2.5: 0x4100, 0.5: 0x3800, [-2]: 0xc000 };
  const bytes = values.flatMap((v) => [known[v] & 0xff, known[v] >> 8]);
  return btoa(String.fromCharCode(...bytes));
}

describe("plume grid decoding", () => {
  it("decodes IEEE half floats", () => {
    expect(halfToFloat(0x3c00)).toBe(1);
    expect(halfToFloat(0x4100)).toBe(2.5);
    expect(halfToFloat(0xc000)).toBe(-2);
    expect(halfToFloat(0x0001)).toBeCloseTo(5.96e-8, 9);                 // smallest subnormal
    expect(halfToFloat(0x7c00)).toBe(Infinity);
  });

  it("decodes a grid and flips it north-up for the canvas", () => {
    const g = { x0: 0, y0: 0, cell_m: 10, nx: 2, ny: 2, max: 2.5, data: f16base64([0, 2.5, 0.5, 1]) };
    expect(Array.from(decodePlume(g))).toEqual([0, 2.5, 0.5, 1]);
    const px = plumeToRGBA(decodePlume(g), 2, 2);
    // canvas row 0 = northern grid row [0.5, 1]; row 1 = southern [0, 2.5]
    expect([px[3] > 0, px[7] > 0, px[11], px[15] > px[7]]).toEqual([true, true, 0, true]);
  });

  it("maps concentration to smoke alpha and node glow", () => {
    expect(smokeAlpha(0.01)).toBe(0);
    expect(smokeAlpha(2.5)).toBeCloseTo(0.75);
    expect(smokeAlpha(10)).toBeCloseTo(0.75);
    expect(glowOpacity(0)).toBe(0);
    expect(glowOpacity(2.5)).toBeCloseTo(0.8);
  });
});

describe("latestPlume", () => {
  const mk = (t: number, fires: boolean, plume: boolean) => ({
    t, fires: fires ? [{ id: 0, x: 0, y: 0, area_m2: 1, age_min: 1, q: 1 }] : [],
    plume: plume ? { x0: 0, y0: 0, cell_m: 10, nx: 1, ny: 1, max: 1, data: "" } : undefined,
  }) as unknown as Frame;
  const frames = [mk(0, false, false), mk(5, true, true), mk(7, true, false), mk(10, true, false), mk(30, true, false),
                  mk(40, false, false)];
  const src = {
    frameAt: (i: number) => frames[i],
    indexAt: (t: number) => frames.reduce((k, f, i) => (f.t <= t ? i : k), 0),
  } as unknown as FrameSource;

  it("returns the newest recent grid while fires burn", () => {
    expect(latestPlume(src, 8, 15)?.t).toBe(5);
    expect(latestPlume(src, 31, 15)).toBeNull();          // too old
    expect(latestPlume(src, 41, 15)).toBeNull();          // no fires now
  });
});
