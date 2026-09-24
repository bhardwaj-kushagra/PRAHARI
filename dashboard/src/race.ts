import type { FrameSource } from "./sources/FrameSource";

/** Phase 9 — race timeline (SPEC View 4): for one fire, the minutes of ignition, the first node candidate near it,
 *  PRAHARI's confirmation, the satellite overpass that sees it and the satellite alert (M37), plus the labelled
 *  deltas. "Near" is the M46 detection radius (150 m) used by every detection count in this project. */

export const RACE_RADIUS_M = 150;

export interface Race {
  fire: number; x: number; y: number; ignition: number;
  candidate: number | null; confirmed: number | null;
  overpass: number | null; platform: string | null; satellite: number | null; missed: number[];
}

export function fireIds(source: FrameSource): number[] {
  const ids: number[] = [];
  for (let i = 0; i < source.frameCount; i++)
    for (const e of source.frameAt(i).events) if (e.type === "ignition" && e.fire !== undefined) ids.push(e.fire);
  return ids;
}

export function raceFor(source: FrameSource, fire: number): Race | null {
  const nodes = source.header.nodes;
  let race: Race | null = null;
  const near = (i: number) => race !== null && Math.hypot(nodes[i].x - race.x, nodes[i].y - race.y) <= RACE_RADIUS_M;
  for (let k = 0; k < source.frameCount; k++) {
    const f = source.frameAt(k);
    for (const e of f.events) {
      if (e.fire !== fire && !(race && e.type === "candidate")) continue;
      if (e.type === "ignition" && !race) {
        race = { fire, x: e.x ?? 0, y: e.y ?? 0, ignition: f.t, candidate: null, confirmed: null,
                 overpass: null, platform: null, satellite: null, missed: [] };
      } else if (race && e.type === "satellite_plan") {
        race.overpass = e.overpass_t ?? null;
        race.platform = e.platform ?? null;
        race.satellite = e.alert_t == null ? null : Math.round(e.alert_t);   // the minute the alert event fires
        race.missed = e.missed ?? [];
      } else if (race && e.type === "satellite_alert" && race.satellite === null) {
        race.satellite = f.t;                                   // stub: fixed delay, no forecast
      } else if (race && e.type === "candidate" && e.node !== undefined && race.candidate === null && near(e.node)) {
        race.candidate = f.t;
      }
    }
    if (race && race.confirmed === null)
      for (const a of f.alerts)
        if ((a.level === "CONFIRMED" || a.level === "ESCALATED") && a.cluster.some(near)) { race.confirmed = f.t; break; }
  }
  return race;
}

/** The headline and the deltas the strip labels (minutes, rounded). */
export function raceDeltas(r: Race): { toCandidate: number | null; toConfirm: number | null; toSatellite: number | null;
                                       lead: number | null; headline: string } {
  const d = (a: number | null) => (a === null ? null : Math.round(a - r.ignition));
  const lead = r.confirmed !== null && r.satellite !== null ? Math.round(r.satellite - r.confirmed) : null;
  const headline = lead === null
    ? (r.confirmed === null ? "PRAHARI did not confirm this fire in the recording" : "No satellite alert within the forecast")
    : lead >= 0 ? `PRAHARI confirmed ${fmtMin(lead)} before the satellite alert`
                : `The satellite alert came ${fmtMin(-lead)} before PRAHARI confirmed`;
  return { toCandidate: d(r.candidate), toConfirm: d(r.confirmed), toSatellite: d(r.satellite), lead, headline };
}

export function fmtMin(m: number): string {
  const h = Math.floor(m / 60);
  return h ? `${h} h ${String(Math.round(m % 60)).padStart(2, "0")} min` : `${Math.round(m)} min`;
}
