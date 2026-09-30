"""Number-to-source table for the paper (charter rule 4): every quotable number, generated from the result files, with
the file and key it comes from. Written to docs/research/numbers.md; never edited by hand."""
from __future__ import annotations

import json
from pathlib import Path

from prahari.record.writer import write_text_atomic


def _load(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def _pct(v):
    return None if v is None else f"{100 * v:.1f}%"


def rows_r1(a: dict) -> list[tuple]:
    """R1: operating points at each budget, pAUC, and the paired comparisons (r1_analysis.json)."""
    out = []
    for name, t in a["test"].items():
        out.append((f"R1 pAUC {name}", f"{t['pauc']:.3f} ({t['pauc_ci95'][0]:.3f}–{t['pauc_ci95'][1]:.3f})",
                    "r1_analysis.json", f"test.{name}.pauc"))
        low = min((p["fa_per_month"] for p in t["curve"] if p["fa_per_month"] is not None), default=None)
        out.append((f"R1 lowest false incidents/month {name}", f"{low:.2f}", "r1_analysis.json", f"test.{name}.curve"))
        for b, x in t["at_budget"].items():
            key = f"test.{name}.at_budget.{b}"
            if not x.get("reachable"):
                out.append((f"R1 {name} at ≤{b}/month", "not reachable", "r1_analysis.json", key))
                continue
            fi = x["false_incidents"]
            out.append((f"R1 {name} at ≤{b}/month: confirmed within 3 h",
                        f"{_pct(x['det'])} ({_pct(x['det_ci95'][0])}–{_pct(x['det_ci95'][1])}); {x['detected']}/{x['fires']}",
                        "r1_analysis.json", key + ".det"))
            out.append((f"R1 {name} at ≤{b}/month: false incidents/month",
                        f"{fi['rate']:.2f} (bootstrap {fi['ci95_bootstrap'][0]:.1f}–{fi['ci95_bootstrap'][1]:.1f})",
                        "r1_analysis.json", key + ".false_incidents"))
            out.append((f"R1 {name} at ≤{b}/month: median latency", f"{x['latency_median_min']} min", "r1_analysis.json",
                        key + ".latency_median_min"))
    for b, fam in a["comparisons"].items():
        for f, comps in fam.items():
            for x, c in comps.items():
                if c.get("reachable"):
                    out.append((f"R1 P2 − {x} at ≤{b}/month (family {f})",
                                f"{100 * c['mean_diff']:+.1f} points ({100 * c['ci95'][0]:+.1f} to {100 * c['ci95'][1]:+.1f}); "
                                f"Wilcoxon p {c['p_wilcoxon']:.2g}, Holm p {c['p_holm']:.2g}; seeds {c['wins']}/{c['losses']}",
                                "r1_analysis.json", f"comparisons.{b}.{f}.{x}"))
    for name, v in a["priors"].items():
        s = v.get("10", {}).get("at_selected_knob")
        if s:
            out.append((f"R1 wrong prior {name} at P2's ≤10 knob", f"{_pct(s['det'])} at {s['fa_per_month']:.2f}/month",
                        "r1_analysis.json", f"priors.{name}.10"))
    return out


def rows_split(h: dict) -> list[tuple]:
    """R2-10: inside/outside-haze split (r1_haze_split.json)."""
    out = [("R1 haze: share of test minutes", _pct(h["haze"]["test_time_share"]), "r1_haze_split.json", "haze.test_time_share"),
           ("R1 haze: fires overlapping haze", f"{h['haze']['fires_overlapping']}/{h['haze']['fires']}", "r1_haze_split.json",
            "haze.fires_overlapping"),
           ("R1 re-run check against the registered run", f"{h['check_against_r1']['seeds_checked']} seeds, "
            f"{len(h['check_against_r1']['mismatches'])} mismatches", "r1_haze_split.json", "check_against_r1")]
    for name, s in h["split"].items():
        out.append((f"R1 {name}: floor (all / outside haze), false incidents/month",
                    f"{s['floor_total']:.2f} / {s['floor_outside']:.2f}", "r1_haze_split.json", f"split.{name}"))
    return out


def rows_real(r: dict, file: str) -> list[tuple]:
    """Real data (REAL): per cluster, events and the node-replay decomposition."""
    out = []
    clusters = r["clusters"] if "clusters" in r else {"ST": r["cluster"]}
    for cl, c in clusters.items():
        nr = c["node_replay"]
        out.append((f"REAL {cl}: common-mode events", f"{c['n_events']} in {c['days_with_share']} days", file,
                    f"clusters.{cl}.n_events" if "clusters" in r else "cluster.n_events"))
        out.append((f"REAL {cl}: node candidates per node per 30 d", str(nr["candidates_per_node_30d"]), file,
                    "node_replay.candidates_per_node_30d"))
        out.append((f"REAL {cl}: exceedance at nominal 1% (outside common mode)", _pct(nr["exceedance_outside_cm_at_1pct"]),
                    file, "node_replay.exceedance_outside_cm_at_1pct"))
        out.append((f"REAL {cl}: share of candidates while ≥ 25% of stations elevated", _pct(nr["share_in_cm_mask"]),
                    file, "node_replay.share_in_cm_mask"))
    return out


def write_numbers(out: Path, doc: Path = Path("docs/research/numbers.md")) -> list[str]:
    """Collect every table the result files allow and write docs/research/numbers.md."""
    out = Path(out)
    rows = []
    a = _load(out / "r1_analysis.json")
    if a:
        rows += rows_r1(a)
    h = _load(out / "r1_haze_split.json")
    if h:
        rows += rows_split(h)
    for f in ("real_thompson2026.json", "real_sensorcommunity_stuttgart.json"):
        r = _load(out / f)
        if r:
            rows += rows_real(r, f)
    lines = ["# Number-to-source table (generated; do not edit)", "",
             "Every number the paper may quote, with the result file (under `results/research/`) and key it comes from. "
             "Regenerate with `python -m prahari.research numbers`. SIM = simulator output; REAL = public data.", "",
             "| Quantity | Value | File | Key |", "| --- | --- | --- | --- |"]
    lines += [f"| {q} | {v} | `{f}` | `{k}` |" for q, v, f, k in rows]
    write_text_atomic(doc, "\n".join(lines) + "\n")
    return [str(doc)]
