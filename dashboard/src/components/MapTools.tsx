import { hasPhase8 } from "../comms";
import { LAYOUT_NAMES, NO_LINK, pct, SF_RAMP } from "../layers";
import { type LayerKey, useMapView } from "../mapView";
import { useSim } from "../store";

/** Grid / corridor / greedy toggle with covered ignition likelihood (M4), plus layer switches with legends. */
export function MapTools() {
  const source = useSim((s) => s.source);
  const { layers, preview, toggleLayer, setPreview } = useMapView();
  const L = source?.header.layouts;
  if (!source) return null;
  const active = L?.active ?? "grid";
  const plumeCard = source.header.model_card.find((m) => m.model === "plume");
  const plumeModel = plumeCard?.equation.startsWith("M11") ? "Gaussian plume (M11)" : "legacy plume (M12)";
  const shown = preview ?? active;
  const p8 = hasPhase8(source.frameAt(0));
  return (
    <div className="map-tools">
      <div className="layout-toggle" role="group" aria-label="Deployment layout">
        <span className="tool-label">Layout</span>
        {LAYOUT_NAMES.filter((n) => L?.[n]).map((n) => (
          <button key={n} className={n === shown ? "on" : ""} aria-pressed={n === shown}
                  onClick={() => setPreview(n === active ? null : n)} data-testid={`layout-${n}`}>
            {n} <b className="mono">{pct(L?.[n]?.covered)}</b>
            {n === active ? <span className="tag">simulated</span> : null}
          </button>
        ))}
        {!L ? <span className="muted small">grid only (recording has no siting data)</span> : null}
        <span className="muted small">of ignition likelihood within {source.header.detection_radius_m ?? 50} m</span>
      </div>
      {preview && preview !== active ? (
        <div className="preview-note" role="note">
          Preview — this recording simulates the <b>{active}</b> layout; hollow circles show where the {preview} layout
          would place the same {source.header.nodes.length} nodes.
        </div>
      ) : null}
      <div className="layer-toggle" role="group" aria-label="Map layers">
        <Layer k="interfaces" on={layers.interfaces} toggle={toggleLayer} label="Interfaces">
          <span className="sw sw-path" /> path <span className="sw sw-road" /> road
          <span className="sw sw-power" /> power line <span className="sw sw-village" /> village
        </Layer>
        <Layer k="likelihood" on={layers.likelihood} toggle={toggleLayer} label="Ignition likelihood">
          <span className="sw-grad" /> low → high (M3, relative)
        </Layer>
        <Layer k="smoke" on={layers.smoke} toggle={toggleLayer} label="Smoke">
          <span className="sw-smoke" /> 0.05 → 2.5 su, log scale · {plumeModel}
        </Layer>
        <Layer k="baselines" on={layers.baselines} toggle={toggleLayer} label="Baselines">
          <span className="sw-p0" /> P0 alarm <span className="sw-p1" /> P1 alarm (last 30 min)
        </Layer>
        <Layer k="links" on={layers.links} toggle={toggleLayer} label="Radio links">
          {[7, 8, 9, 10, 11, 12].map((sf) => (
            <span key={sf} className="sf-key"><span className="sw-line" style={{ background: SF_RAMP[sf] }} />SF{sf}</span>
          ))}
          <span className="sf-key"><span className="sw-ring" style={{ borderColor: NO_LINK }} />no link</span>
        </Layer>
        {p8.comms ? (
          <Layer k="packets" on={layers.packets} toggle={toggleLayer} label="Packets">
            <span className="sw-line pk-delivered-key" /> delivered <span className="sw-line pk-lost-key" /> collided
            <span className="sw-badge" /> queued · thick = candidate, thin = heartbeat (M39–M40)
          </Layer>
        ) : null}
        {p8.energy ? (
          <Layer k="energy" on={layers.energy} toggle={toggleLayer} label="Stored energy">
            <span className="sw-ring soc-key-0" /> standard <span className="sw-ring soc-key-1" /> ULP &lt; 20%
            <span className="sw-ring soc-key-2" /> off &lt; 5% · ring filled to state of charge (M43)
          </Layer>
        ) : null}
        <Layer k="coverage" on={layers.coverage} toggle={toggleLayer} label="Detection radius">
          <span className="sw-disk" /> {source.header.detection_radius_m ?? 50} m
        </Layer>
        <Layer k="satellite" on={layers.satellite} toggle={toggleLayer} label="Satellite pixels">
          <span className="sw sw-sat" /> {source.header.satellite_pixel_m ?? 375} m
        </Layer>
      </div>
    </div>
  );
}

function Layer({ k, on, toggle, label, children }: {
  k: LayerKey; on: boolean; toggle: (k: LayerKey) => void; label: string; children: React.ReactNode;
}) {
  return (
    <label className={`layer ${on ? "on" : ""}`}>
      <input type="checkbox" checked={on} onChange={() => toggle(k)} data-testid={`layer-${k}`} />
      <span className="layer-name">{label}</span>
      {on ? <span className="layer-key">{children}</span> : null}
    </label>
  );
}
