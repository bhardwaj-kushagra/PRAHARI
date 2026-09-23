import { sci, simClock } from "../format";
import { pct } from "../layers";
import { useFrame, useSim } from "../store";
import { SimBadge } from "./SimBadge";

export function HeaderStrip() {
  const source = useSim((s) => s.source);
  const simT = useSim((s) => s.simT);
  const frame = useFrame();
  const h = source?.header;
  return (
    <header className="strip">
      <div className="brand">
        <span className="brand-name">PRAHARI-SIM</span>
        <SimBadge />
      </div>
      {h && frame ? (
        <dl className="strip-stats">
          <div><dt>Scenario</dt><dd>{h.scenario}</dd></div>
          <div><dt>Layout</dt><dd>{h.layouts?.active ?? "grid"} · <b className="mono" data-testid="coverage">{pct(h.layouts?.[h.layouts.active]?.covered)}</b> likelihood covered</dd></div>
          <div><dt>Clock</dt><dd className="mono" data-testid="clock">{simClock(h, simT)}</dd></div>
          <div><dt>Day type</dt><dd>{frame.prior.day_type === "dry_busy" ? "dry / busy" : "wet / quiet"}</dd></div>
          <div><dt>Prior odds</dt><dd className="mono">{sci(frame.prior.odds)}</dd></div>
          <div><dt>Required quorum</dt><dd>today: <b className="mono">{frame.prior.quorum}</b> nodes must agree</dd></div>
          <div><dt>Weather</dt><dd className="mono">{frame.weather.T} °C · {frame.weather.RH}% · FFMC {frame.weather.ffmc}</dd></div>
        </dl>
      ) : (
        <span className="muted">No recording loaded</span>
      )}
    </header>
  );
}
