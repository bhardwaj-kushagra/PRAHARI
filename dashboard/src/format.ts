import type { Header } from "./types";

/** "Day 1 · 14:07" from the header start time plus simulated minutes. */
export function simClock(header: Header, t: number): string {
  const start = new Date(header.start + "Z");
  const d = new Date(start.getTime() + Math.floor(t) * 60_000);
  const day = Math.floor((d.getTime() - Date.UTC(start.getUTCFullYear(), start.getUTCMonth(), start.getUTCDate())) / 86_400_000) + 1;
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  return `Day ${day} · ${hh}:${mm}`;
}

export function sci(v: number, digits = 2): string {
  if (!Number.isFinite(v)) return "—";
  if (v === 0) return "0";
  const a = Math.abs(v);
  if (a < 1e-2 || a >= 1e4) return v.toExponential(digits - 1).replace(/\.0+e/, "e");
  const s = v.toPrecision(digits + 1);
  return s.includes(".") ? s.replace(/0+$/, "").replace(/\.$/, "") : s;
}

export function daysLabel(days: number, fromMin?: number): string {
  const base = `${days} simulated day${days === 1 ? "" : "s"}`;
  return fromMin ? `${base}, recorded from day ${Math.floor(fromMin / 1440) + 1}` : base;
}
