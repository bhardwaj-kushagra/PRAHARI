import { useState } from "react";
import { create } from "zustand";
import { connectLive } from "../sources/LiveSource";
import { beginLoad, isLatestLoad, useSim } from "../store";

interface LiveState { server: string; status: string; stop: (() => void) | null; setServer: (s: string) => void }

/** Live-mode connection state, shared with the mechanism switches (which POST module changes in live mode). */
export const useLive = create<LiveState>((set) => ({
  server: "http://localhost:8000", status: "not connected", stop: null,
  setServer: (server) => set({ server }),
}));

interface Scenario { name: string; description: string; days: number }

/** Optional live engine (SPEC §6.1, Phase 6): start a run on the FastAPI server and stream its frames.
 *  Replay needs none of this; if the server is absent the dashboard carries on with recordings. */
export function LivePanel() {
  const { server, status, stop, setServer } = useLive();
  const [open, setOpen] = useState(false);
  const [list, setList] = useState<Scenario[]>([]);
  const [chosen, setChosen] = useState("");
  const [speed, setSpeed] = useState(600);
  const say = (s: string) => useLive.setState({ status: s });

  async function load() {
    try {
      const r = await fetch(`${server}/scenarios`);
      const j: Scenario[] = await r.json();
      setList(j);
      setChosen(j.find((s) => s.name === "node_3day")?.name ?? j[0]?.name ?? "");
      say(`${j.length} scenarios on the server`);
    } catch {
      say("server not reachable — replay still works (uvicorn server.app:app)");
    }
  }

  async function start() {
    stop?.();
    try {
      const r = await fetch(`${server}/run`, { method: "POST", headers: { "Content-Type": "application/json" },
                                                body: JSON.stringify({ scenario: chosen, speed }) });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
    } catch (e) {
      say(`could not start: ${e instanceof Error ? e.message : String(e)}`);
      return;
    }
    let first = true;
    const token = beginLoad();                   // opening a recording (or a presenter step) ends this live view
    let close: () => void = () => undefined;
    close = connectLive(server, (view, buf) => {
      if (!isLatestLoad(token)) { close(); useLive.setState({ stop: null }); say("live view closed — another recording is open"); return; }
      const sim = useSim.getState();
      if (first) { sim.setSource(view); first = false; } else sim.updateSource(view);
      say(`live · ${buf.header?.scenario} · t = ${buf.frames[buf.frames.length - 1].t} min`);
    }, (buf) => {
      say(buf.error ? `closed: ${buf.error}` : buf.footer ? "live run finished" : "disconnected");
      useLive.setState({ stop: null });
    });
    useLive.setState({ stop: close });
    say("connecting…");
  }

  return (
    <div className="live" data-testid="live-panel">
      <button className="linkish" onClick={() => setOpen(!open)} aria-expanded={open}>Live engine {open ? "▾" : "▸"}</button>
      <span className="muted small"> {status}</span>
      {open ? (
        <div className="live-row">
          <input aria-label="Server URL" value={server} onChange={(e) => setServer(e.target.value)} size={22} />
          <button onClick={load}>Scenarios</button>
          <select aria-label="Scenario" value={chosen} onChange={(e) => setChosen(e.target.value)}>
            {list.map((s) => <option key={s.name} value={s.name} title={s.description}>{s.name} ({s.days} d)</option>)}
          </select>
          <select aria-label="Speed" value={speed} onChange={(e) => setSpeed(Number(e.target.value))}>
            {[60, 600, 3600, 0].map((v) => <option key={v} value={v}>{v ? `×${v}` : "max"}</option>)}
          </select>
          <button onClick={start} disabled={!chosen}>Start</button>
          {stop ? <button onClick={() => stop()}>Stop</button> : null}
        </div>
      ) : null}
    </div>
  );
}
