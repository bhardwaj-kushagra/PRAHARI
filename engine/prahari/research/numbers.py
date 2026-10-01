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


def rows_sweeps(w: dict) -> list[tuple]:
    """R1 sensitivity sweeps (r1_sweeps.json): per point, P2 and P2-med at their strictest knob and at 10 a month."""
    out = []
    for lab, sw in w["sweeps"].items():
        for name in ("P2", "P2-med"):
            q = sw["pipelines"].get(name)
            if not q:
                continue
            d = q["10"]["det_at_equal_fa"]
            out.append((f"R1 sweep {lab} {name}: false incidents/month at the strictest knob; detection at 10/month",
                        f"{q['fa_at_first_knob']}; {'not reachable' if not d else _pct(d)}", "r1_sweeps.json",
                        f"sweeps.{lab}.pipelines.{name}"))
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
        j = min(range(len(s["total_per_month"])), key=lambda k: s["total_per_month"][k])
        out.append((f"R1 {name}: at the floor knob ({s['grid'][j]}), inside / outside haze per month; share inside",
                    f"{s['inside_per_month'][j]} / {s['outside_per_month'][j]}; {_pct(s['inside_share'][j])}",
                    "r1_haze_split.json", f"split.{name}.inside_share[{j}]"))
    for name, f in h.get("fires_by_haze_at_10", {}).items():
        o, n = f["overlap"], f["no_overlap"]
        out.append((f"R1 {name} at ≤10/month: detection, fires overlapping haze / not",
                    f"{o['detected']}/{o['fires']} / {n['detected']}/{n['fires']}", "r1_haze_split.json",
                    f"fires_by_haze_at_10.{name}"))
    return out


def rows_r2(a: dict) -> list[tuple]:
    """R2 (SIM): B*, every scenario's floors with their haze split, detection at B*, and families F and D."""
    f = "r2_analysis.json"
    out = [("R2 B* (false incidents/month, set on the H-mix selection seeds)", str(a["b_star"]), f, "b_star")]
    for sc, s in a["scenarios"].items():
        tag = f"R2 {sc}" + ("" if s["complete"] else " (incomplete)")
        for name, m in s["methods"].items():
            key = f"scenarios.{sc}.methods.{name}"
            fl = m["floor_at_selected_knob"]
            fi, d = fl["false_incidents"], fl["decomposition"]
            out.append((f"{tag} {name}: floor, false incidents/month (selected knob {fl['cell']})",
                        f"{fi['rate']:.2f} (bootstrap {fi['ci95_bootstrap'][0]:.2f}–{fi['ci95_bootstrap'][1]:.2f}); "
                        f"inside haze {d['inside']}, outside {d['outside']}", f, key + ".floor_at_selected_knob"))
            out.append((f"{tag} {name}: own floor", f"{m['own_floor']['fa_per_month']} at {m['own_floor']['cell']}",
                        f, key + ".own_floor"))
            b = m.get("at_b_star")
            if b:
                out.append((f"{tag} {name}: confirmed within 3 h at B*",
                            f"{_pct(b['det'])} ({_pct(b['det_ci95'][0])}–{_pct(b['det_ci95'][1])}); "
                            f"{b['detected']}/{b['fires']}; {b['false_incidents']['rate']:.2f} false incidents/month",
                            f, key + ".at_b_star"))
            if a["b_star"] is not None:
                out.append((f"{tag} {name}: detection at equal FA = B*", _pct(m["det_at_equal_fa"][str(a["b_star"])]),
                            f, key + ".det_at_equal_fa"))
        for fam, comps in s.get("families", {}).items():
            for x, c in comps.items():
                if c.get("reachable"):
                    scale, unit = (1, " /month") if fam == "F" else (100, " points")
                    out.append((f"{tag} {x} − P2 (family {fam})",
                                f"{scale * c['mean_diff']:+.2f}{unit} ({scale * c['ci95'][0]:+.2f} to "
                                f"{scale * c['ci95'][1]:+.2f}); Wilcoxon p {c['p_wilcoxon']:.2g}, Holm p {c['p_holm']:.2g}",
                                f, f"scenarios.{sc}.families.{fam}.{x}"))
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


def rows_india(r: dict) -> list[tuple]:
    """Addendum C (REAL): per cluster-year events, rates and the held-out comparison; pooled per cluster; DL15 node
    replay; provenance check."""
    f, out = "real_india.json", []
    for key, c in r["clusters"].items():
        k = f"clusters.{key}"
        if not c.get("analysed"):
            out.append((f"REAL India {key}", f"not analysed: {c.get('reason')}", f, k))
            continue
        h = c["held_out"]
        out.append((f"REAL India {key}: stations, events", f"{c['stations']} stations; {c['n_events']} events in "
                    f"{c['days_with_share']} days ({c['events_per_day']}/day, ×{h['rate_multiplier_vs_h_mix']} H-mix)",
                    f, k + ".held_out.events_per_day"))
        out.append((f"REAL India {key}: night share (Wilson 95%)",
                    f"{h['night_share']} ({h['night_share_ci95_wilson']}); reference 0.7", f, k + ".held_out.night_share"))
        out.append((f"REAL India {key}: amplitude CV median; share inside operator 90%",
                    f"{h['cv_median']}; {h['cv_share_inside_operator_90']} (operator {h['cv_operator_q05_50_95']})",
                    f, k + ".held_out.cv_median"))
        out.append((f"REAL India {key}: onset spread median (min); share inside operator 90%",
                    f"{h['onset_spread_median_min']}; {h['onset_spread_share_inside_operator_90']} "
                    f"(operator {h['onset_spread_operator_q05_50_95']})", f, k + ".held_out.onset_spread_median_min"))
        if c.get("node_replay", {}).get("candidates_per_node_30d") is not None:
            nr = c["node_replay"]
            out.append((f"REAL India {key}: node candidates per node per 30 d; share while ≥ 25% elevated",
                        f"{nr['candidates_per_node_30d']}; {_pct(nr['share_in_cm_mask'])}", f, k + ".node_replay"))
            out.append((f"REAL India {key}: exceedance at nominal 1% (outside common mode)",
                        _pct(nr["exceedance_outside_cm_at_1pct"]), f, k + ".node_replay.exceedance_outside_cm_at_1pct"))
        if "co" in c and c["co"].get("n_events") is not None:
            out.append((f"REAL India {key}: CO events; share of PM events overlapping a CO event",
                        f"{c['co']['n_events']}; {c['co']['share_pm_events_overlapping_co']}", f, k + ".co"))
    for cl, pl in r["pooled"].items():
        out.append((f"REAL India {cl} pooled: events per day; night share (Wilson 95%)",
                    f"{pl['events_per_day']} (×{pl['rate_multiplier_vs_h_mix']} H-mix); {pl['night_share']} "
                    f"({pl['night_share_ci95_wilson']})", f, f"pooled.{cl}"))
    pv = r.get("provenance_2017", {})
    if pv.get("median_abs_rel_diff_all") is not None:
        out.append(("REAL India provenance: OpenAQ vs Princeton CPCB, 2017, median abs. relative difference",
                    f"{pv['median_abs_rel_diff_all']} over {pv['hours']} station-hours ({pv['matched']} stations)",
                    f, "provenance_2017"))
    return out


def write_numbers(out: Path, doc: Path = Path("docs/research/numbers.md")) -> list[str]:
    """Collect every table the result files allow and write docs/research/numbers.md."""
    out = Path(out)
    rows = []
    a = _load(out / "r1_analysis.json")
    if a:
        rows += rows_r1(a)
    w = _load(out / "r1_sweeps.json")
    if w:
        rows += rows_sweeps(w)
    h = _load(out / "r1_haze_split.json")
    if h:
        rows += rows_split(h)
    ri = _load(out / "real_india.json")
    if ri:
        rows += rows_india(ri)
    a2 = _load(out / "r2_analysis.json")
    if a2:
        rows += rows_r2(a2)
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
