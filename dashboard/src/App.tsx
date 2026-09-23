import { useEffect } from "react";
import { AlertsPanel } from "./components/AlertsPanel";
import { CommandMap } from "./components/CommandMap";
import { Footer } from "./components/Footer";
import { HeaderStrip } from "./components/HeaderStrip";
import { ModuleHealth } from "./components/ModuleHealth";
import { NodePanel } from "./components/NodePanel";
import { openFile, RecordingPicker } from "./components/RecordingPicker";
import { TimeControls } from "./components/TimeControls";
import { type Panel, useSim } from "./store";

const TABS: [Panel, string][] = [["health", "Health & model card"], ["node", "Node"], ["alerts", "Alerts"]];

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
  return (
    <div className="app">
      <HeaderStrip />
      <main className="body">
        <section className="left"><CommandMap /></section>
        <aside className="right">
          <RecordingPicker />
          <nav className="tabs" role="tablist">
            {TABS.map(([id, label]) => (
              <button key={id} role="tab" aria-selected={panel === id} className={panel === id ? "on" : ""} onClick={() => setPanel(id)}>{label}</button>
            ))}
          </nav>
          <div className="panel">
            {panel === "health" ? <ModuleHealth /> : panel === "node" ? <NodePanel /> : <AlertsPanel />}
          </div>
        </aside>
      </main>
      <TimeControls />
      <Footer />
    </div>
  );
}
