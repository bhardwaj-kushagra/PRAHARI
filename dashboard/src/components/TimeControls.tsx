import { useMemo } from "react";
import { simClock } from "../format";
import { SPEEDS, useSim } from "../store";

const MARK_ROW: Record<string, number> = { ignition: 0, alert: 1, satellite: 2, candidate: 3, degraded: 4 };

export function TimeControls() {
  const source = useSim((s) => s.source);
  const simT = useSim((s) => s.simT);
  const playing = useSim((s) => s.playing);
  const speed = useSim((s) => s.speed);
  const { togglePlay, setSpeed, seek, stepFrame } = useSim.getState();
  const marks = useMemo(() => source?.eventMarks() ?? [], [source]);
  if (!source) return null;
  const [t0, t1] = source.span;
  const pct = (t: number) => (t1 > t0 ? ((t - t0) / (t1 - t0)) * 100 : 0);
  return (
    <section className="controls" aria-label="Time controls">
      <div className="buttons">
        <button onClick={() => stepFrame(-1)} aria-label="Step back one frame">◀︎</button>
        <button onClick={togglePlay} className="play" aria-label={playing ? "Pause" : "Play"} data-testid="play">
          {playing ? "❚❚ Pause" : "▶ Play"}
        </button>
        <button onClick={() => stepFrame(1)} aria-label="Step forward one frame">▶︎</button>
        <span className="speeds" role="group" aria-label="Playback speed">
          {SPEEDS.map((s) => (
            <button key={s} className={s === speed ? "on" : ""} aria-pressed={s === speed} onClick={() => setSpeed(s)}>×{s}</button>
          ))}
        </span>
        <span className="mono clock">{simClock(source.header, simT)} · t = {Math.floor(simT)} min</span>
      </div>
      <div className="scrub">
        <svg className="marks" viewBox="0 0 100 10" preserveAspectRatio="none" aria-hidden="true">
          {marks.map((m, i) => (
            <rect key={i} x={pct(m.t) - 0.08} y={MARK_ROW[m.kind] * 2} width={0.16} height={2} className={`mark mark-${m.kind}`} />
          ))}
        </svg>
        <input type="range" min={t0} max={t1} step={1} value={Math.floor(simT)}
               onChange={(e) => seek(Number(e.target.value))} aria-label="Scrub simulated time" />
        <div className="mark-legend">
          <span className="k-ignition">ignition</span><span className="k-alert">alert</span>
          <span className="k-satellite">satellite alert</span><span className="k-candidate">candidate</span>
          <span className="k-degraded">module degraded</span>
        </div>
      </div>
    </section>
  );
}
