import { useEffect, useState } from "react";
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
  const source = useSim((s) => s.source);
  const loading = useSim((s) => s.loading);
  const error = useSim((s) => s.error);

  useEffect(() => {
    fetch(`${BASE}index.json`)
      .then((r) => (r.ok ? r.json() : { recordings: [] }))
      .then((j: { recordings: string[] }) => {
        setList(j.recordings);
        const want = new URLSearchParams(location.search).get("rec") ?? j.recordings.find((n) => n.startsWith("smoke")) ?? j.recordings[0];
        if (want && !useSim.getState().source) openWith(() => RecordingSource.fromUrl(BASE + want));
      })
      .catch(() => setList([]));
  }, []);

  return (
    <div className="picker">
      <label>
        Recording{" "}
        <select value={source && list.includes(source.name) ? source.name : ""}
                onChange={(e) => e.target.value && openWith(() => RecordingSource.fromUrl(BASE + e.target.value))}>
          <option value="">{list.length ? "choose…" : "none bundled"}</option>
          {list.map((n) => <option key={n} value={n}>{n}</option>)}
        </select>
      </label>
      <label className="file">
        Open file…
        <input type="file" accept=".gz,.jsonl" onChange={(e) => e.target.files?.[0] && openFile(e.target.files[0])} />
      </label>
      {loading ? <span className="muted">loading…</span> : null}
      {error ? <span className="err" role="alert">{error}</span> : null}
    </div>
  );
}
