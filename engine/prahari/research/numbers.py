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
    out = [("R2 B* (false incidents/month, set on the H-mix selection seeds)", str(a["b_star"]), f, "b_star"),
           ("R2 B* under the R2-D1 validity rule", "undefined (no budget reached by every compared method)"
            if a.get("b_star_R2_D1") is None else str(a["b_star_R2_D1"]), f, "b_star_R2_D1")]
    for sc, s in a["scenarios"].items():
        tag = f"R2 {sc}" + ("" if s["complete"] else " (incomplete)")
        for name, m in s["methods"].items():
            key = f"scenarios.{sc}.methods.{name}"
            fl = m["floor_at_selected_knob"]
            fi, d = fl["false_incidents"], fl["decomposition"]
            flag = "; INVALID (R2-D1: continuous alarming)" if fl.get("valid_here") is False else ""
            out.append((f"{tag} {name}: floor, false incidents/month (selected knob {fl['cell']})",
                        f"{fi['rate']:.2f} (bootstrap {fi['ci95_bootstrap'][0]:.2f}–{fi['ci95_bootstrap'][1]:.2f}); "
                        f"inside haze {d['inside']}, outside {d['outside']} (share inside {_pct(d['share_inside'])}); "
                        f"detection {_pct(fl['det'])}{flag}", f, key + ".floor_at_selected_knob"))
            out.append((f"{tag} {name}: own floor", f"{m['own_floor']['fa_per_month']} at {m['own_floor']['cell']}",
                        f, key + ".own_floor"))
            out.append((f"{tag} {name}: detection at equal FA (R8; 0 below the curve's floor), per budget",
                        "; ".join(f"{x}: {_pct(v)}" for x, v in m["det_at_equal_fa"].items()), f,
                        key + ".det_at_equal_fa"))
            b = m.get("at_b_star")
            if b:
                out.append((f"{tag} {name}: confirmed within 3 h at B*",
                            f"{_pct(b['det'])} ({_pct(b['det_ci95'][0])}–{_pct(b['det_ci95'][1])}); "
                            f"{b['detected']}/{b['fires']}; {b['false_incidents']['rate']:.2f} false incidents/month"
                            + ("; INVALID (R2-D1)" if b.get("valid_here") is False else ""),
                            f, key + ".at_b_star"))
        for fam, comps in s.get("sensitivity_R2_D1", {}).get("families", {}).items():
            for x, c in comps.items():
                out.append((f"{tag} [R2-D1] {x} − P2 (family {fam})",
                            "not computable (B* undefined)" if not c.get("reachable") else
                            f"{c['mean_diff']:+.3f}; Holm p {c['p_holm']:.2g}", f,
                            f"scenarios.{sc}.sensitivity_R2_D1.families.{fam}.{x}"))
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
    """Real data (REAL): per cluster, stations, spacing, events and their rate, and the node-replay decomposition."""
    out = []
    clusters = r["clusters"] if "clusters" in r else {"ST": r["cluster"]}
    for cl, c in clusters.items():
        nr = c["node_replay"]
        k = f"clusters.{cl}" if "clusters" in r else "cluster"
        out.append((f"REAL {cl}: stations; median spacing (km)", f"{c['stations']}; {c['spacing_km']['median']}", file,
                    k + ".spacing_km"))
        out.append((f"REAL {cl}: common-mode events", f"{c['n_events']} in {c['days_with_share']} days", file,
                    k + ".n_events"))
        out.append((f"REAL {cl}: common-mode events per day", str(c["events_per_day"]), file, k + ".events_per_day"))
        out.append((f"REAL {cl}: node replay test days", str(nr["test_days"]), file, k + ".node_replay.test_days"))
        out.append((f"REAL {cl}: node candidates per node per 30 d", str(nr["candidates_per_node_30d"]), file,
                    k + ".node_replay.candidates_per_node_30d"))
        out.append((f"REAL {cl}: exceedance at nominal 1% (outside common mode)", _pct(nr["exceedance_outside_cm_at_1pct"]),
                    file, k + ".node_replay.exceedance_outside_cm_at_1pct"))
        out.append((f"REAL {cl}: share of candidates while ≥ 25% of stations elevated", _pct(nr["share_in_cm_mask"]),
                    file, k + ".node_replay.share_in_cm_mask"))
    return out


def rows_r3(a: dict) -> list[tuple]:
    """R3 (SIM): B*, the head-to-head tests H1/H2 (P2-medSCMR − P2-gate), each method's floor and detection at B*."""
    f = "r3_analysis.json"
    out = [("R3 B* (both compared methods, valid settings, H-mix selection seeds)", str(a["b_star"]), f, "b_star")]
    for name, m in a["selection"]["methods"].items():
        key = f"selection.methods.{name}"
        if m["floor"]:
            fl = m["floor"]
            out.append((f"R3 selection {name}: floor setting (selection seeds: FA/month, detection)",
                        f"{fl['cell']}: {fl['fa_per_month']:g}, {_pct(fl['det'])}", f, key + ".floor"))
        for b, o in m["operating"].items():
            if o:
                out.append((f"R3 selection {name}: operating setting at {b}/month (selection seeds: FA/month, "
                            f"detection)", f"{o['cell']}: {o['fa_per_month']:g}, {_pct(o['det'])}", f,
                            key + f".operating.{b}"))
        out.append((f"R3 selection {name}: invalid settings (≥ 24 h incident)", str(m["invalid_cells"]), f,
                    key + ".invalid_cells"))
    for sc, s in a["scenarios"].items():
        tag = f"R3 {sc}" + ("" if s["complete"] else " (incomplete)")
        h = s["head_to_head"]
        for b, d in h.get("descriptive_by_budget", {}).items():
            if not d.get("reachable"):
                out.append((f"{tag} descriptive at {b}/month", "not reachable by both", f,
                            f"scenarios.{sc}.head_to_head.descriptive_by_budget.{b}"))
                continue
            c = d["paired"]
            out.append((f"{tag} descriptive at {b}/month (P2-medSCMR − P2-gate, detection; each: detection, FA/month)",
                        f"P2-medSCMR {_pct(d['P2-medSCMR']['det'])}, {d['P2-medSCMR']['fa_per_month']:.2f}; P2-gate "
                        f"{_pct(d['P2-gate']['det'])}, {d['P2-gate']['fa_per_month']:.2f}; difference "
                        f"{100 * c['mean_diff']:+.2f} ({100 * c['ci95'][0]:+.2f} to {100 * c['ci95'][1]:+.2f}); "
                        f"Wilcoxon p {c['p_wilcoxon']:.2g} (unadjusted); seeds {c['wins']}/{c['losses']}", f,
                        f"scenarios.{sc}.head_to_head.descriptive_by_budget.{b}"))
        for key, label in (("H1_detection_at_b_star", "detection at B*"), ("H2_floor", "floor, false incidents/month")):
            c = h.get(key, {})
            if c.get("reachable") is False:
                out.append((f"{tag} {key}", "not computable", f, f"scenarios.{sc}.head_to_head.{key}"))
                continue
            scale = 100 if key.startswith("H1") else 1
            holm = f", Holm p {c['p_holm']:.2g}" if "p_holm" in c else ""
            out.append((f"{tag} {key} (P2-medSCMR − P2-gate, {label})",
                        f"{scale * c['mean_diff']:+.2f} ({scale * c['ci95'][0]:+.2f} to {scale * c['ci95'][1]:+.2f}); "
                        f"Wilcoxon p {c['p_wilcoxon']:.2g}{holm}; seeds {c['wins']}/{c['losses']}", f,
                        f"scenarios.{sc}.head_to_head.{key}"))
        for name, m in s["methods"].items():
            key = f"scenarios.{sc}.methods.{name}"
            fl = m["floor_at_selected_knob"]
            if fl:
                fi = fl["false_incidents"]
                out.append((f"{tag} {name}: floor, false incidents/month (setting {fl['cell']})",
                            f"{fi['rate']:.2f} (bootstrap {fi['ci95_bootstrap'][0]:.2f}–{fi['ci95_bootstrap'][1]:.2f}); "
                            f"inside haze {fl['decomposition']['inside']}, outside {fl['decomposition']['outside']} "
                            f"(share inside {_pct(fl['decomposition']['share_inside'])}); detection {_pct(fl['det'])}; "
                            f"valid {fl['valid_here']}", f, key + ".floor_at_selected_knob"))
            own = m["own_floor"]
            out.append((f"{tag} {name}: own lowest floor on these seeds", f"{own['fa_per_month']:.2f} at {own['cell']} "
                        f"(detection {_pct(own['det'])})", f, key + ".own_floor"))
            out.append((f"{tag} {name}: detection at equal FA (R8; 0 below the curve's floor), per budget",
                        "; ".join(f"{x}: {_pct(v)}" for x, v in m["det_at_equal_fa"].items()), f,
                        key + ".det_at_equal_fa"))
            b = m.get("at_b_star")
            if b:
                out.append((f"{tag} {name}: confirmed within 3 h at B*",
                            f"{_pct(b['det'])} ({_pct(b['det_ci95'][0])}–{_pct(b['det_ci95'][1])}); "
                            f"{b['false_incidents']['rate']:.2f} false incidents/month", f, key + ".at_b_star"))
                ov = b["by_haze_overlap"]
                out.append((f"{tag} {name}: at B*, mean time to confirmation (miss = 180 min), median latency; fires "
                            f"overlapping haze / not", f"{b['mean_ttc_min']} min, {b['latency_median_min']} min; "
                            f"{_pct(ov['overlap']['det'])} ({ov['overlap']['detected']} of {ov['overlap']['fires']}) / "
                            f"{_pct(ov['no_overlap']['det'])} ({ov['no_overlap']['detected']} of {ov['no_overlap']['fires']})",
                            f, key + ".at_b_star.by_haze_overlap"))
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
        if c.get("spacing_km"):
            out.append((f"REAL India {key}: median station spacing (km)", str(c["spacing_km"]["median"]), f,
                        k + ".spacing_km"))
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
            out.append((f"REAL India {key}: node replay test days", str(nr["test_days"]), f, k + ".node_replay.test_days"))
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


def rows_r4_selection(a: dict) -> list[tuple]:
    """R4 (SIM) selection, per scenario on its own selection seeds: operating settings at every budget, the floor, the
    useful floor and both floors without r < 0.1 (selection seeds; FA/month, detection)."""
    f, out = "r4_selection.json", []
    for sc, sel in a["selection"].items():
        for name, m in sel["methods"].items():
            key = f"selection.{sc}.methods.{name}"
            for b, o in m["operating"].items():
                out.append((f"R4 selection {sc} {name}: operating setting at {b}/month (FA/month, detection)",
                            "not reached" if o is None else f"{o['cell']}: {o['fa_per_month']:g}, {_pct(o['det'])}",
                            f, key + f".operating[{b}]"))
            for k in ("floor", "useful_floor", "floor_r_ge_0.1", "useful_floor_r_ge_0.1"):
                o = m.get(k)
                out.append((f"R4 selection {sc} {name}: {k.replace('_', ' ')} setting (FA/month, detection)",
                            "none" if o is None else f"{o['cell']}: {o['fa_per_month']:g}, {_pct(o['det'])}", f,
                            key + f"[{k}]"))
            out.append((f"R4 selection {sc} {name}: invalid settings (≥ 24 h incident)", str(m["invalid_cells"]), f,
                        key + ".invalid_cells"))
    return out


def _pts(c: dict) -> str:
    return (f"{100 * c['mean_diff']:+.2f} points ({100 * c['ci95'][0]:+.2f} to {100 * c['ci95'][1]:+.2f}); "
            f"Wilcoxon p {c['p_wilcoxon']:.2g}")


def rows_r4(a: dict) -> list[tuple]:
    """R4 (SIM) analysis: family P with Holm, the price at the other budgets (both views), every scenario's detection
    at 1 a month with E5 and time to confirmation, equal-FA detection, all floors with their haze split, the capped
    shares, the dose table and the method differences."""
    f, out = "r4_analysis.json", []
    for m, c in a["family_P"].items():
        k = f"family_P[{m}]"
        if c.get("reachable") is False:
            out.append((f"R4 family P {m}", "not computable", f, k))
            continue
        out.append((f"R4 family P {m}: detection at 1/month, H-none − H-mix (cells {c['H-none_cell']} / {c['H-mix_cell']})",
                    f"{_pts(c)}, Holm p {c['p_holm']:.2g} ({'rejected' if c['reject'] else 'not rejected'}); "
                    f"seeds {c['wins']}/{c['losses']} of {c['n_seeds']}", f, k))
    for b, d in a["descriptive"]["price_by_budget"].items():
        for m, c in d.items():
            k = f"descriptive.price_by_budget[{b}][{m}]"
            val = (f"not computable (reached: H-none {c['H-none_reached']}, H-mix {c['H-mix_reached']})"
                   if c.get("reachable") is False else f"{_pts(c)} (unadjusted); seeds {c['wins']}/{c['losses']}")
            out.append((f"R4 price of haze {m} at {b}/month (deployment; H-none − H-mix)", val, f, k))
    for m, d in a["descriptive"]["price_at_equal_fa"].items():
        out.append((f"R4 price of haze {m} at equal FA (R8; points, H-none − H-mix) per budget",
                    "; ".join(f"{b}: {100 * v:+.1f}" for b, v in d.items()), f, f"descriptive.price_at_equal_fa[{m}]"))
    for sc, s in a["scenarios"].items():
        for m, r in s["methods"].items():
            k = f"scenarios[{sc}].methods[{m}]"
            b = r.get("at_b_star")
            if b:
                ov = b["by_haze_overlap"]
                out.append((f"R4 {sc} {m}: at 1/month (setting {b['cell']}): detection; FA/month; mean TTC; median latency",
                            f"{_pct(b['det'])} ({_pct(b['det_ci95'][0])}–{_pct(b['det_ci95'][1])}); "
                            f"{b['false_incidents']['rate']:.2f}; {b['mean_ttc_min']} min; {b['latency_median_min']} min",
                            f, k + "[at_b_star]"))
                out.append((f"R4 {sc} {m}: at 1/month, fires overlapping haze / not",
                            f"{_pct(ov['overlap']['det'])} ({ov['overlap']['detected']} of {ov['overlap']['fires']}) / "
                            f"{_pct(ov['no_overlap']['det'])} ({ov['no_overlap']['detected']} of "
                            f"{ov['no_overlap']['fires']})", f, k + "[at_b_star][by_haze_overlap]"))
            out.append((f"R4 {sc} {m}: detection at equal FA (R8; 0 = not reachable) per budget",
                        "; ".join(f"{x}: {_pct(v)}" for x, v in r["det_at_equal_fa"].items()), f, k + "[det_at_equal_fa]"))
        for m, fl in s["floors"].items():
            for kind in ("floor", "useful_floor", "floor_r_ge_0.1", "useful_floor_r_ge_0.1"):
                v = fl[kind]
                k = f"scenarios[{sc}].floors[{m}][{kind}]"
                if v is None:
                    out.append((f"R4 {sc} {m}: {kind.replace('_', ' ')}", "none", f, k))
                    continue
                fi, dc = v["false_incidents"], v["decomposition"]
                out.append((f"R4 {sc} {m}: {kind.replace('_', ' ')} (setting {v['cell']}): FA/month (95% CI); detection; "
                            f"inside / outside haze (share inside)",
                            f"{fi['rate']:.2f} ({fi['ci95_bootstrap'][0]:.2f}–{fi['ci95_bootstrap'][1]:.2f}); "
                            f"{_pct(v['det'])}; {dc['inside']} / {dc['outside']} ({_pct(dc['share_inside'])}); "
                            f"valid {v['valid_here']}", f, k))
            out.append((f"R4 {sc} {m}: share of capped node thresholds by target",
                        "; ".join(f"{t}: {_pct(c)}" for t, c in fl["share_capped_by_target"].items()), f,
                        f"scenarios[{sc}].floors[{m}][share_capped_by_target]"))
        for b, pairs in s["method_differences"].items():
            for pair, c in pairs.items():
                k = f"scenarios[{sc}].method_differences[{b}][{pair}]"
                out.append((f"R4 {sc} at {b}/month: {pair} (detection, per seed; descriptive)",
                            "not reachable by both" if not c.get("reachable") else
                            f"{_pts(c)} (unadjusted); seeds {c['wins']}/{c['losses']}", f, k))
    for sc, d in a["descriptive"]["dose_response"].items():
        for m, v in d["methods"].items():
            k = f"descriptive.dose_response[{sc}].methods[{m}]"
            out.append((f"R4 dose {sc} {m} (seeds ≤ 6050, {d['selection_from']} settings): detection at 1/month (FA); "
                        f"at equal FA; at 3/month (FA); at equal FA",
                        f"{_pct(v['det_at_1'])} ({v['fa_at_1']}); {_pct(v['det_at_equal_fa_1'])}; {_pct(v['det_at_3'])} "
                        f"({v['fa_at_3']}); {_pct(v['det_at_equal_fa_3'])}", f, k))
            for key in ("floor_at_selected", "useful_floor_at_selected", "own_floor"):
                o = v[key]
                out.append((f"R4 dose {sc} {m}: {key.replace('_', ' ')} (FA/month, detection)",
                            "none" if o is None else f"{o['cell']}: {o['fa_per_month']}, {_pct(o['det'])}", f,
                            k + f"[{key}]"))
    return out


_STRICT = {"target": ("node", min), "rho": ("rho", max), "theta": ("theta", min), "h_M": ("h_mei", max)}


def strict_edges(knob: str, cell, grids: dict) -> list[str]:
    """Audit of 7 Oct 2026: the knob axes on which a selected setting sits at the strict end of its registered grid
    (smallest target r, largest SCMR ratio ρ, smallest gate share θ, largest Mei threshold), so the optimum may lie
    beyond the grid. 'off' (None) is a natural end of the grid, not an edge."""
    vals = cell if isinstance(cell, list) else [cell]
    out = []
    for ax, v in zip(knob.split("×"), vals):
        g, pick = _STRICT[ax]
        if v is not None and v == pick([x for x in grids[g] if x is not None]):
            out.append(f"{ax} = {v:g}")
    return out


def _lowest(cells: list[dict]):
    """The lowest false-incident cell, ties to the higher detection, then the first (as analysis_r2.floor_index)."""
    j = min(range(len(cells)), key=lambda i: (cells[i]["fa_per_month"], -cells[i]["det"], i))
    return j, cells[j]


def rows_audit(sweeps: dict | None, rounds: dict, grids: dict, r1: dict | None = None) -> list[tuple]:
    """Audit of 7 Oct 2026 (docs/research/audit-2026-10-07.md; descriptive): the textbook-threshold range over the R1
    sweeps, P2's lowest rate at R1's fixed SCMR ratio (ρ = 3) against any ρ in R2 and R3, the share of floor incidents
    inside haze per method across scenarios, and the selected settings that sit on a strict grid edge."""
    out = []
    if r1:
        c = r1["test"]["P0"]["curve"]
        j, lo = _lowest(c)
        out.append(("Audit R1 P0: at its strictest knob (its floor), false incidents/month; detection",
                    f"{lo['fa_per_month']} at k = {lo['knob']:g}; {_pct(lo['det'])}", "r1_analysis.json",
                    f"test.P0.curve[{j}]"))
    if sweeps:
        pts = {k: v["pipelines"]["P1"]["fa_at_first_knob"] for k, v in sweeps["sweeps"].items() if "P1" in v["pipelines"]}
        out.append(("Audit R1 sweeps: P1 at the textbook threshold (h = 8.8), false incidents/month, range over points",
                    f"{min(pts.values()):.1f}–{max(pts.values()):.1f} ({len(pts)} points)", "r1_sweeps.json",
                    "sweeps.<point>.pipelines.P1.fa_at_first_knob"))
        for pt in ("haze=0", "default", "haze=3", "haze=6"):
            for name in ("P2", "P2-med", "AR"):
                p = sweeps["sweeps"].get(pt, {}).get("pipelines", {}).get(name)
                if p:
                    out.append((f"Audit R1 sweep {pt} {name}: detection at equal FA (R8; 0 = not reachable) at 1 / 3 / "
                                f"10 per month", " / ".join(_pct(p[b]["det_at_equal_fa"]) for b in ("1", "3", "10")),
                                "r1_sweeps.json", f"sweeps.{pt}.pipelines.{name}.<budget>.det_at_equal_fa"))
    for rnd, (f, a) in rounds.items():
        for sc, s in a["scenarios"].items():
            amoc = s["methods"]["P2"]["amoc"]
            r3 = [i for i, c in enumerate(amoc) if c["cell"][1] == 3.0]
            j3 = r3[_lowest([amoc[i] for i in r3])[0]]
            ja, ca = _lowest(amoc)
            c3 = amoc[j3]
            out.append((f"Audit {rnd} {sc} P2: lowest false incidents/month at ρ = 3 (R1's fixed ratio) vs at any ρ",
                        f"{c3['fa_per_month']:.2f} at {c3['cell']} (detection {_pct(c3['det'])}) vs {ca['fa_per_month']:.2f} "
                        f"at {ca['cell']} (detection {_pct(ca['det'])})", f, f"scenarios.{sc}.methods.P2.amoc[{j3}], [{ja}]"))
        names = list(next(iter(a["scenarios"].values()))["methods"])
        for name in names:
            sh = {sc: s["methods"][name]["floor_at_selected_knob"]["decomposition"]["share_inside"]
                  for sc, s in a["scenarios"].items()}
            vals = [v for v in sh.values() if v is not None]
            if vals:
                out.append((f"Audit {rnd} {name}: share of floor incidents inside haze, range over scenarios",
                            f"{_pct(min(vals))}–{_pct(max(vals))} (" + ", ".join(f"{k} {_pct(v)}" for k, v in sh.items())
                            + ")", f, f"scenarios.<s>.methods.{name}.floor_at_selected_knob.decomposition.share_inside"))
        for name, m in a["selection"]["methods"].items():
            sets = [("floor", m["floor"])] + [(f"operating {b}/month", o) for b, o in m["operating"].items()]
            for what, o in sets:
                if o and strict_edges(m["knob"], o["cell"], grids):
                    out.append((f"Audit {rnd} selection {name}: {what} setting on a strict grid edge",
                                f"{o['cell']}: " + ", ".join(strict_edges(m["knob"], o["cell"], grids)), f,
                                f"selection.methods.{name}." + ("floor" if what == "floor" else f"operating.{what.split()[1][:-6]}")))
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
    a3 = _load(out / "r3_analysis.json")
    if a3:
        rows += rows_r3(a3)
    ri = _load(out / "real_india.json")
    if ri:
        rows += rows_india(ri)
    a2 = _load(out / "r2_analysis.json")
    if a2:
        rows += rows_r2(a2)
    s4 = _load(out / "r4_selection.json")
    if s4:
        rows += rows_r4_selection(s4)
    a4 = _load(out / "r4_analysis.json")
    if a4:
        rows += rows_r4(a4)
    for f in ("real_thompson2026.json", "real_sensorcommunity_stuttgart.json"):
        r = _load(out / f)
        if r:
            rows += rows_real(r, f)
    rounds = {k: (f, x) for k, f, x in (("R2", "r2_analysis.json", a2), ("R3", "r3_analysis.json", a3)) if x}
    if rounds:
        from prahari.research.runner_r2 import load_r2
        rows += rows_audit(w, rounds, load_r2()["grids"], a)
    lines = ["# Number-to-source table (generated; do not edit)", "",
             "Every number the paper may quote, with the result file (under `results/research/`) and key it comes from. "
             "Regenerate with `python -m prahari.research numbers`. SIM = simulator output; REAL = public data.", "",
             "| Quantity | Value | File | Key |", "| --- | --- | --- | --- |"]
    lines += [f"| {q} | {v} | `{f}` | `{k}` |" for q, v, f, k in rows]
    write_text_atomic(doc, "\n".join(lines) + "\n")
    return [str(doc)]
