import { lazy, Suspense, useEffect } from "react";
import { AlertsPanel } from "./components/AlertsPanel";
import { CommandMap } from "./components/CommandMap";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Footer } from "./components/Footer";
import { HeaderStrip } from "./components/HeaderStrip";
import { MapTools } from "./components/MapTools";
import { RaceTimeline } from "./components/RaceTimeline";
import { ModuleHealth } from "./components/ModuleHealth";
import { PresenterOverlay } from "./components/PresenterOverlay";
import { NodePanel } from "./components/NodePanel";
import { LivePanel } from "./components/LivePanel";
import { openFile, RecordingPicker } from "./components/RecordingPicker";
import { TimeControls } from "./components/TimeControls";
import { SiteBar } from "./site/SiteBar";
import { LIVE_ENGINE } from "./site/siteConfig";
import { type Panel, useSim } from "./store";

// Charts (ECharts) load only when the Signals tab opens, keeping the map view light.
const SignalsPanel = lazy(() => import("./components/SignalsPanel").then((m) => ({ default: m.SignalsPanel })));

const ResultsPanel = lazy(() => import("./components/ResultsPanel").then((m) => ({ default: m.ResultsPanel })));

const NodeInspector = lazy(() => import("./components/NodeInspector").then((m) => ({ default: m.NodeInspector })));

const TABS: [Panel, string][] = [
  ["health", "Health & model card"], ["signals", "Signals"], ["node", "Node"], ["alerts", "Alerts"], ["results", "Results"],
];

function usePlayback() {
  const playing = useSim((s) => s.playing);
  useEffect(() => {
    if (!playing) return;
    let last = performance.now();
    let id = requestAnimationFrame(function loop(now) {
      useSim.getState().advance((now - last) / 1000);
      last = now;
      id = requestAnimationFrame(loop);
    });
    return () => cancelAnimationFrame(id);
  }, [playing]);
}

function useKeys() {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).tagName === "INPUT" || (e.target as HTMLElement).tagName === "SELECT") return;
      const s = useSim.getState();
      if (e.code === "Space") { e.preventDefault(); s.togglePlay(); }
      else if (e.key === "ArrowRight") s.stepFrame(1);
      else if (e.key === "ArrowLeft") s.stepFrame(-1);
      else if (e.key === "Escape") s.selectNode(null);
    };
    const onDrop = (e: DragEvent) => {
      e.preventDefault();
      const f = e.dataTransfer?.files?.[0];
      if (f) openFile(f);
    };
    const onDragOver = (e: DragEvent) => e.preventDefault();
    window.addEventListener("keydown", onKey);
    window.addEventListener("drop", onDrop);
    window.addEventListener("dragover", onDragOver);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("drop", onDrop);
      window.removeEventListener("dragover", onDragOver);
    };
  }, []);
}

export function App() {
  usePlayback();
  useKeys();
  const panel = useSim((s) => s.panel);
  const setPanel = useSim((s) => s.setPanel);
  const rec = useSim((s) => s.source?.name ?? "");
  const loading = <p className="muted">Loading charts…</p>;
  return (
    <div className="app">
      <div className="top"><SiteBar />{/* site: FIRENET / AgniWare bar */}<ErrorBoundary name="header" resetKey={rec}><HeaderStrip /></ErrorBoundary><PresenterOverlay /></div>
      <main className="body">
        <section className="left">
          <ErrorBoundary name="map" resetKey={rec}><MapTools /><CommandMap /></ErrorBoundary>
          <ErrorBoundary name="race timeline" resetKey={rec}><RaceTimeline /></ErrorBoundary>
        </section>
        <aside className="right">
          <ErrorBoundary name="recording picker"><RecordingPicker />{LIVE_ENGINE && <LivePanel />}</ErrorBoundary>
          <nav className="tabs" role="tablist">
            {TABS.map(([id, label]) => (
              <button key={id} role="tab" aria-selected={panel === id} className={panel === id ? "on" : ""} onClick={() => setPanel(id)}>{label}</button>
            ))}
          </nav>
          <div className="panel">
            {/* One boundary per tab: a failing view says so; the other tabs, the map and the keys keep working. */}
            <ErrorBoundary name={TABS.find(([id]) => id === panel)?.[1] ?? panel} resetKey={`${rec}|${panel}`}>
              {panel === "health" ? <ModuleHealth /> : panel === "signals"
                ? <Suspense fallback={loading}><SignalsPanel /></Suspense>
                : panel === "results" ? <Suspense fallback={loading}><ResultsPanel /></Suspense>
                : panel === "node" ? (
                  <><NodePanel /><Suspense fallback={loading}><NodeInspector /></Suspense></>
                ) : <AlertsPanel />}
            </ErrorBoundary>
          </div>
        </aside>
      </main>
      <ErrorBoundary name="time controls" resetKey={rec}><TimeControls /></ErrorBoundary>
      <Footer />
    </div>
  );
}
