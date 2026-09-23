import { describe, expect, it } from "vitest";
import { glyphScale, lambdaToRGBA, NO_LINK, pct, pixelCaption, SF_RAMP, sfColour, svgPoints } from "./layers";

describe("map layer helpers", () => {
  it("colours links by spreading factor with a grey no-link fallback", () => {
    expect(sfColour(7)).toBe(SF_RAMP[7]);
    expect(sfColour(12)).toBe(SF_RAMP[12]);
    expect(sfColour(null)).toBe(NO_LINK);
    expect(sfColour(6)).toBe(NO_LINK);
    expect(Object.keys(SF_RAMP).map(Number)).toEqual([7, 8, 9, 10, 11, 12]);
  });

  it("derives the satellite-pixel caption instead of hard-coding it", () => {
    expect(pixelCaption(375, 70).cells).toBe(29);        // (375 / 70)² = 28.7 (SPEC §6.2, DER)
    expect(pixelCaption(375, 150).cells).toBe(6);
    expect(pixelCaption(375, 70).text).toContain("≈ 29 node cells at 70 m");
  });

  it("flips the likelihood raster so north is up and maps value to alpha", () => {
    // 2 × 2 grid, row 0 = south: [0, 1] south, [0.5, 0] north
    const px = lambdaToRGBA([0, 1, 0.5, 0], 2, 2, [10, 20, 30], 1);
    const alpha = [px[3], px[7], px[11], px[15]];
    expect(alpha).toEqual([128, 0, 0, 255]);             // canvas row 0 is the northern row
    expect([px[0], px[1], px[2]]).toEqual([10, 20, 30]);
  });

  it("scales glyphs with the map and formats coverage", () => {
    expect(glyphScale(700)).toBe(1);
    expect(glyphScale(1400)).toBe(2);
    expect(glyphScale(300)).toBe(1);
    expect(svgPoints([[0, 0], [10, 20]], 100)).toBe("0,100 10,80");
    expect(pct(0.8326)).toBe("83%");
    expect(pct(null)).toBe("—");
  });
});
