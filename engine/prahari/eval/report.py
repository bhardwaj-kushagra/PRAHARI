"""Combine experiment presets into `results/summary.json` in the report's table format (SPEC §9.3, Phase 7).

`golden.json` is the primary table (P0, P1, P1t, P2 and the edge ablations, node metrics, the operating dial);
`ablation.json` adds the node-layer ablations, `spacing.json` the spacing sweep and `seeds20.json` the 20-seed sweep.
A preset run with no `golden.json` beside it (for example a short test) is its own primary table.
"""
from __future__ import annotations

import json
from pathlib import Path

ORDER = ("P0", "P1", "P1t", "P2", "P2-QCC", "P2-TTC", "P2-SCMR", "P2-RAQ")
LABELS = {"P0": "P0 fixed threshold", "P1": "P1 v1 as written", "P1t": "P1t v1 replay-tuned", "P2": "P2 PRAHARI",
          "P2-QCC": "P2 minus QCC", "P2-TTC": "P2 minus TTC", "P2-SCMR": "P2 minus SCMR", "P2-RAQ": "P2 minus RAQ"}


def _load(out: Path, name: str):
    f = out / f"{name}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else None


def table(pipes: dict, reference: dict | None) -> list[dict]:
    """One row per pipeline in the report's order: our numbers beside the report's (labelled)."""
    ref = (reference or {}).get("pipelines", {})
    rows = []
    for name in [n for n in ORDER if n in pipes] + [n for n in pipes if n not in ORDER]:
        p = pipes[name]
        fa, det = p["false_incidents_per_month"], p["confirmed_within_3h"]
        rows.append({"pipeline": name, "label": LABELS.get(name, name), "false_incidents_per_month": fa["rate"],
                     "ci95": fa["ci95"], "confirmed_within_3h": det["rate"], "confirmed_ci95": det["ci95"],
                     "report": ref.get(name)})
    return rows


def combine(out_dir: str | Path, primary: str | None = None) -> dict:
    out = Path(out_dir)
    golden = _load(out, "golden")
    base = golden if golden is not None else (_load(out, primary) if primary else None)
    if base is None:
        return {}
    summary = dict(base)
    summary["pipelines"] = dict(base["pipelines"])
    sources = {base["preset"]: {"seeds": base["seeds"]}}
    ablation = _load(out, "ablation")
    if ablation and base is golden:
        summary["pipelines"].update(ablation["pipelines"])
        summary["ablation_form"] = ablation.get("ablation_form", "stub")     # form of the node ablations (P7-12)
        sources["ablation"] = {"seeds": ablation["seeds"], "ablation_form": summary["ablation_form"]}
    spacing = _load(out, "spacing")
    if spacing and base is golden:
        summary["spacing"] = {"seeds": spacing["seeds"], "rows": [
            {"spacing_m": int(sp), **{k: s["pipelines"]["P2"][k] for k in ("confirmed_within_3h", "single_node_within_3h",
                                                                          "false_incidents_per_month", "latency_median_min")}}
            for sp, s in sorted(spacing["by_spacing"].items(), key=lambda kv: int(kv[0]))]}
        sources["spacing"] = {"seeds": spacing["seeds"]}
    sweep = _load(out, "seeds20")
    if sweep and base is golden:
        summary["seed_sweep"] = {"seeds": sweep["seeds"], "pipelines": sweep["pipelines"]}
        sources["seeds20"] = {"seeds": sweep["seeds"]}
    summary["sources"] = sources
    summary["table"] = table(summary["pipelines"], summary.get("reference"))
    (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary
