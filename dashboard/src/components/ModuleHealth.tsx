import { useFrame, useSim } from "../store";

/** View 7 — module health and the model card (SPEC §6.2). */
export function ModuleHealth() {
  const source = useSim((s) => s.source);
  const frame = useFrame();
  if (!source || !frame) return null;
  const card = source.header.model_card;
  const final = source.footer?.health ?? {};
  return (
    <div className="health">
      <h2>Module health and model card</h2>
      <p className="muted">
        State now comes from the current frame; errors from the end of the run. <code>real</code> = full model,
        <code>stub</code> = simple fallback, <code>off</code> = bypassed, <code>degraded</code> = switched to a fallback after a failure.
      </p>
      <table>
        <thead>
          <tr><th>Module</th><th>Config</th><th>Now</th><th>Model</th><th>Tag</th><th>Errors</th></tr>
        </thead>
        <tbody>
          {card.map((row) => {
            const now = frame.health[row.model] ?? "?";
            const end = final[row.model];
            return (
              <tr key={row.model} className={`state-${now}`}>
                <td className="mono">{row.model}</td>
                <td>{source.header.modules[row.model]}</td>
                <td><span className={`pill pill-${now}`}>{now === "ok" ? "real" : now}</span></td>
                <td>
                  <div>{row.description}</div>
                  <div className="muted mono small">{row.equation} · v{row.version}{row.source ? ` · ${row.source}` : ""}</div>
                  {end?.last_error ? <div className="err small">{end.last_error} (t = {end.degraded_at})</div> : null}
                </td>
                <td className="mono">{row.tag}</td>
                <td className="mono">{end?.errors ?? 0}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
