import { useMemo, useState } from "react";
import { minuteLabel } from "../series";
import { fireIds, fmtMin, raceDeltas, raceFor } from "../race";
import { useSim } from "../store";

interface Mark { t: number; label: string; cls: string; above: boolean }

/** SPEC View 4 — the race strip under the map: ignition, first node candidate, PRAHARI confirmation, the overpass
 *  that sees the fire and the satellite alert (M37), with the deltas labelled. Every value is simulator output. */
export function RaceTimeline() {
  const source = useSim((s) => s.source);
  const simT = useSim((s) => s.simT);
  const ids = useMemo(() => (source ? fireIds(source) : []), [source]);
  const [pick, setPick] = useState<number | null>(null);
  const fire = pick !== null && ids.includes(pick) ? pick : ids[0];
  const race = useMemo(() => (source && fire !== undefined ? raceFor(source, fire) : null), [source, fire]);
  if (!source || !race) return null;
  const d = raceDeltas(race);
  const marks: Mark[] = [
    { t: race.ignition, label: "ignition", cls: "rk-ignition", above: true },
    ...(race.candidate !== null ? [{ t: race.candidate, label: `first node candidate · +${fmtMin(d.toCandidate!)}`, cls: "rk-candidate", above: false }] : []),
    ...(race.confirmed !== null ? [{ t: race.confirmed, label: `PRAHARI confirmed · +${fmtMin(d.toConfirm!)}`, cls: "rk-prahari", above: true }] : []),
    ...(race.overpass !== null ? [{ t: race.overpass, label: `${race.platform} overpass`, cls: "rk-overpass", above: false }] : []),
    ...(race.satellite !== null ? [{ t: race.satellite, label: `satellite alert · +${fmtMin(d.toSatellite!)}`, cls: "rk-satellite", above: true }] : []),
  ];
  const t0 = race.ignition;
  const t1 = Math.max(...marks.map((m) => m.t), t0 + 60) + 30;
  const W = 1000;
  const x = (t: number) => 40 + ((t - t0) / (t1 - t0)) * (W - 80);
  // Label layout: a label within 190 px of the previous one on its side moves one level further out.
  const last: Record<string, number> = {};
  const level = marks.map((m) => {
    const side = m.above ? "a" : "b";
    const lv = last[side] !== undefined && x(m.t) - last[side] < 190 ? 1 : 0;
    last[side] = lv === 1 ? -1e9 : x(m.t);
    return lv;
  });
  const Y = 72;
  return (
    <section className="race" data-testid="race-timeline" aria-label="race timeline">
      <div className="race-head">
        <b>Race timeline</b>
        {ids.length > 1 ? (
          <select value={fire} onChange={(e) => setPick(Number(e.target.value))} aria-label="fire">
            {ids.map((i) => <option key={i} value={i}>fire F{i}</option>)}
          </select>
        ) : <span className="muted small">fire F{race.fire}</span>}
        <span className="race-headline" data-testid="race-headline">{d.headline} · SIM</span>
      </div>
      <svg viewBox={`0 0 ${W} 134`} role="img" aria-label={d.headline}>
        <line x1={x(t0)} x2={x(t1)} y1={Y} y2={Y} className="race-axis" />
        {race.confirmed !== null && race.satellite !== null ? (
          <line x1={x(race.confirmed)} x2={x(race.satellite)} y1={Y} y2={Y} className="race-lead" />
        ) : null}
        {race.missed.map((t) => (
          <g key={`m${t}`} transform={`translate(${x(t)},${Y})`}><path d="M-4,-4L4,4M4,-4L-4,4" className="rk-missed" />
            <title>{`overpass at ${minuteLabel(t)} missed the fire (cloud or canopy) · SIM`}</title></g>
        ))}
        {marks.map((m, k) => {
          const s = m.above ? -1 : 1;
          const r = 14 + 26 * level[k];
          return (
            <g key={k} transform={`translate(${x(m.t)},${Y})`} className={m.cls}>
              <line y1={s * r} y2={0} className="rk-stem" />
              <circle r={5} className="rk-dot" />
              <text y={m.above ? -r - 4 : r + 12} textAnchor={k === 0 ? "start" : "middle"} className="rk-label">{m.label}</text>
              <text y={m.above ? -r - 16 : r + 24} textAnchor={k === 0 ? "start" : "middle"} className="rk-time">{minuteLabel(m.t)}</text>
            </g>
          );
        })}
        {simT >= t0 && simT <= t1 ? <line x1={x(simT)} x2={x(simT)} y1={Y - 12} y2={Y + 12} className="race-cursor" /> : null}
      </svg>
      <p className="chart-foot">SIMULATION · seed {source.header.seed} · candidate and confirmation within {150} m of the
        ignition (M46) · satellite: M37 overpasses at fixed local times, 500 m² threshold and processing delay — illustrative</p>
    </section>
  );
}
