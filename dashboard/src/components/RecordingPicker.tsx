import { useEffect, useState } from "react";
import { cardLine, filterByRegime, regimeOptions, type RecordingMeta } from "../regimes";
import { RecordingSource } from "../sources/RecordingSource";
import { useSim } from "../store";

const BASE = `${import.meta.env.BASE_URL}recordings/`;

async function openWith(load: () => Promise<RecordingSource>) {
  const { setLoading, setSource, setError } = useSim.getState();
  setLoading(true);
  try {
    setSource(await load());
  } catch (e) {
    setError(e instanceof Error ? e.message : String(e));
  } finally {
    setLoading(false);
  }
}

export function openFile(file: File) {
  return openWith(() => RecordingSource.fromFile(file));
}

/** Choose a bundled recording or open one from disk (no server needed, SPEC P8). */
export function RecordingPicker() {
  const [list, setList] = useState<string[]>([]);
  const [meta, setMeta] = useState<Record<string, RecordingMeta>>({});
  const [regime, setRegime] = useState("");
  const source = useSim((s) => s.source);
  const loading = useSim((s) => s.loading);
  const error = useSim((s) => s.error);

  useEffect(() => {
    fetch(`${BASE}index.json`)
      .then((r) => (r.ok ? r.json() : { recordings: [] }))
      .then((j: { recordings: string[]; meta?: Record<string, RecordingMeta> }) => {
        setList(j.recordings);
        setMeta(j.meta ?? {});
        const want = new URLSearchParams(location.search).get("rec") ?? j.recordings.find((n) => n.startsWith("smoke")) ?? j.recordings[0];
        if (want && !useSim.getState().source) openWith(() => RecordingSource.fromUrl(BASE + want));
      })
      .catch(() => setList([]));
  }, []);

  // View 8 — regime selector: filter the bundled recordings by the Regime Card they ran under (SPEC §8.1).
  const regimes = regimeOptions(list, meta);
  const shown = filterByRegime(list, meta, regime);
  const card = source?.header.regime;
  return (
    <div className="picker">
      {regimes.length > 1 ? (
        <label>
          Regime{" "}
          <select value={regime} onChange={(e) => setRegime(e.target.value)} data-testid="regime-select">
            <option value="">all ({list.length})</option>
            {regimes.map((o) => <option key={o.name} value={o.name}>{o.label} ({o.n})</option>)}
          </select>
        </label>
      ) : null}
      <label>
        Recording{" "}
        <select value={source && shown.includes(source.name) ? source.name : ""}
                onChange={(e) => e.target.value && openWith(() => RecordingSource.fromUrl(BASE + e.target.value))}>
          <option value="">{shown.length ? "choose…" : "none bundled"}</option>
          {shown.map((n) => <option key={n} value={n} title={meta[n]?.description}>{n}</option>)}
        </select>
      </label>
      {card && card.name !== "none" ? (
        <span className="regime-card" data-testid="regime-card" title={`Regime Card ${card.name} (SPEC §8.1)`}>
          <b>{card.label}</b> <span className="muted small">{cardLine(card)}</span>
        </span>
      ) : null}
      <label className="file">
        Open file…
        <input type="file" accept=".gz,.jsonl" onChange={(e) => e.target.files?.[0] && openFile(e.target.files[0])} />
      </label>
      {loading ? <span className="muted">loading…</span> : null}
      {error ? <span className="err" role="alert">{error}</span> : null}
    </div>
  );
}
