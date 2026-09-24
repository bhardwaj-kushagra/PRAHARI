/** Phase 9 — Regime Cards (SPEC §8.1, View 8). Each recording's header names the card it ran under; the bundled
 *  index carries the same block per file so the picker can filter recordings by regime without opening them. */
export interface RegimeCard { name: string; label: string; radio_plan: string; alert_format: string; lightning: boolean }
export interface RecordingMeta { scenario?: string; description?: string; seed?: number; days?: number; regime?: RegimeCard | null }

/** Recordings made before Phase 9 carry no card: they ran on configs/default.yaml alone. */
export const NO_CARD = "none";

export function regimeOf(m: RecordingMeta | undefined): string {
  return m?.regime?.name ?? NO_CARD;
}

/** The regimes present among the bundled recordings, each with its label, cards first and "no card" last. */
export function regimeOptions(files: string[], meta: Record<string, RecordingMeta>): { name: string; label: string; n: number }[] {
  const seen = new Map<string, { name: string; label: string; n: number }>();
  for (const f of files) {
    const name = regimeOf(meta[f]);
    const label = name === NO_CARD ? "no card (default)" : meta[f]?.regime?.label ?? name;
    const o = seen.get(name) ?? { name, label, n: 0 };
    o.n += 1;
    seen.set(name, o);
  }
  return [...seen.values()].sort((a, b) => Number(a.name === NO_CARD) - Number(b.name === NO_CARD) || a.name.localeCompare(b.name));
}

export function filterByRegime(files: string[], meta: Record<string, RecordingMeta>, regime: string): string[] {
  return regime === "" ? files : files.filter((f) => regimeOf(meta[f]) === regime);
}

/** One-line card summary for the header strip. */
export function cardLine(c: RegimeCard): string {
  return `${c.radio_plan} · alerts: ${c.alert_format} · lightning ${c.lightning ? "on" : "off"}`;
}
