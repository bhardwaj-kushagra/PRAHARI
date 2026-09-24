import { useEffect, useMemo, useState } from "react";
import { runCounters, SWITCHES, variantName } from "../edge";
import { RecordingSource } from "../sources/RecordingSource";
import { beginLoad, isLatestLoad, useSim } from "../store";
import type { Frame } from "../types";
import { useLive } from "./LivePanel";

const BASE = `${import.meta.env.BASE_URL}recordings/`;
const LABEL: Record<string, string> = { ttc: "TTC", qcc: "QCC", scmr: "SCMR", raq: "RAQ", srp: "SRP" };

/** SPEC §6.2 View 5 — mechanism switches with live counters. In replay they open the pre-recorded variant of the
 *  same scenario and seed (keeping the clock); in live mode they reconfigure the running engine. */
export function MechanismSwitches() {
  const source = useSim((s) => s.source);
  const simT = useSim((s) => s.simT);
  const server = useLive((s) => s.server);
  const [recs, setRecs] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    fetch(`${BASE}index.json`).then((r) => (r.ok ? r.json() : { recordings: [] }))
      .then((j: { recordings: string[] }) => setRecs(j.recordings)).catch(() => setRecs([]));
  }, []);
  const idx = source ? source.indexAt(simT) : 0;
  const frames = useMemo<Frame[]>(() => (source ? Array.from({ length: source.frameCount }, (_, i) => source.frameAt(i)) : []),
                                   [source]);
  const counters = useMemo(() => (source ? runCounters(frames, source.header.nodes, idx) : null), [frames, idx, source]);
  if (!source || !counters) return null;
  const live = source.kind === "live";
  const frame = source.frameAt(idx);

  async function toggle(module: string, to: string) {
    if (!source) return;
    setBusy(true);
    try {
      if (live) {
        await fetch(`${server}/modules`, { method: "POST", headers: { "Content-Type": "application/json" },
                                           body: JSON.stringify({ module, state: to }) });
      } else {
        const token = beginLoad();
        const src = await RecordingSource.fromUrl(BASE + variantName(source.name, module, to));
        if (isLatestLoad(token)) useSim.getState().updateSource(src);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="switches" data-testid="switches" aria-label="Mechanism switches">
      <h2>Mechanisms <span className="muted small">{live ? "live: switches reconfigure the running engine" : "replay: pre-recorded variants"}</span></h2>
      <div className="switch-row">
        {SWITCHES.map((m) => {
          const state = live ? (frame.health[m] ?? source.header.modules[m]) : source.header.modules[m];
          const on = state === "real";
          const to = on ? "stub" : "real";
          const available = live || recs.includes(variantName(source.name, m, to));
          return (
            <button key={m} className={`switch ${on ? "on" : ""}`} aria-pressed={on} disabled={busy || !available}
                    title={available ? `switch ${LABEL[m]} to ${to}` : "no pre-recorded variant; use live mode"}
                    onClick={() => toggle(m, to)} data-testid={`switch-${m}`}>
              {LABEL[m]} <span className="small">{on ? "real" : state}</span>
            </button>
          );
        })}
      </div>
      <p className="counters small">
        So far: <b className="mono">{counters.falseAlarms}</b> false alarm{counters.falseAlarms === 1 ? "" : "s"} ·{" "}
        <b className="mono">{counters.detected}/{counters.fires}</b> fires confirmed within 3 h
        {counters.medianLatency !== null ? <> · median <b className="mono">{counters.medianLatency}</b> min</> : null} · SIM
      </p>
    </section>
  );
}
