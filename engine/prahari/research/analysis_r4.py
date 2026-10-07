"""Protocol R4 analysis (docs/research/protocol-r4.md): the price of haze at strict false-alarm budgets.

Selection (§5), per scenario on its own selection seeds (H-none, H-mix), valid cells only: the operating point at every
budget, the floor, the useful floor (the lowest false incidents among cells whose pooled detection is at least 50%),
and both floors with the strict node targets r < 0.1 left out. Family P (§6), on the test seeds: per method, per-seed
detection at 1 a month in H-none minus H-mix, each at its own operating point, paired by seed number; two-sided
Wilcoxon with a paired seed-bootstrap interval; Holm across the three methods. Everything else is descriptive. Writes
`r4_selection.json` (selection only) or also `r4_test.json` and `r4_analysis.json`. All SIM.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from prahari.core.rng import make_rngs
from prahari.record.writer import write_text_atomic
from prahari.research import pstats as ps
from prahari.research.analysis import _json, _r, by_pipeline
from prahari.research.analysis_r2 import compact_r2, det_at_equal_fa, scenario_results, selection_r2, valid_cells
from prahari.research.analysis_r3 import load_stage

STRICT_TARGET = 0.1          # §5 — floors are also selected without the node targets below this value


def _target(cell) -> float:
    return float(cell[0] if isinstance(cell, list) else cell)


def useful_floor_index(fa, det, allowed, min_det: float):
    """§5 — the lowest pooled false incidents among allowed cells with pooled detection ≥ min_det; ties: higher
    detection, then the first cell. None when no cell qualifies."""
    cells = [j for j in range(len(fa)) if (allowed is None or allowed[j]) and det[j] >= min_det]
    return int(min(cells, key=lambda j: (fa[j], -det[j], j))) if cells else None


def _cell_summary(m: dict, pc: dict, j):
    return None if j is None else {"index": j, "cell": m["grid"][j], "fa_per_month": _r(pc["fa"][j]), "det": _r(pc["det"][j])}


def selection_r4(rows: list[dict], r4: dict) -> dict:
    """§5 for one scenario: R2's selection with the validity rule (operating points, floor), plus the useful floor and
    both floors without r < 0.1."""
    sel = selection_r2(rows, {**r4, "compared": r4["methods"]}, validity=True)
    sel["b_star"] = r4["primary_budget"]                      # R4 reports every method at the primary budget
    for name, prow in by_pipeline(rows).items():
        m = ps.seed_matrix(prow)
        pc = ps.pooled(m)
        valid = valid_cells(prow) or [True] * len(m["grid"])
        loose = [v and _target(c) >= STRICT_TARGET for v, c in zip(valid, m["grid"])]
        s = sel["methods"][name]
        s["useful_floor"] = _cell_summary(m, pc, useful_floor_index(pc["fa"], pc["det"], valid, r4["useful_detection"]))
        jf = min((j for j in range(len(m["grid"])) if loose[j]), key=lambda j: (pc["fa"][j], -pc["det"][j], j),
                 default=None)
        s["floor_r_ge_0.1"] = _cell_summary(m, pc, jf)
        s["useful_floor_r_ge_0.1"] = _cell_summary(m, pc, useful_floor_index(pc["fa"], pc["det"], loose,
                                                                            r4["useful_detection"]))
    return sel


def _by_seed(rows: list[dict]) -> dict:
    return {r["seed"]: r for r in rows}


def _det_at(rows: list[dict], name: str, j) -> np.ndarray:
    m = ps.seed_matrix(by_pipeline(rows)[name])
    return ps.per_seed_det(m, j)


def price_of_haze(rows_none: list[dict], rows_mix: list[dict], sel_none: dict, sel_mix: dict, r4: dict, W,
                  budget: float) -> dict:
    """§6 — per method, per-seed detection at `budget` in H-none minus H-mix (each at its own operating point),
    matched by seed number."""
    a, b = _by_seed(rows_none), _by_seed(rows_mix)
    seeds = sorted(set(a) & set(b))
    ra, rb = [a[s] for s in seeds], [b[s] for s in seeds]
    out = {}
    for name in r4["methods"]:
        oa = sel_none["methods"][name]["operating"].get(str(budget))
        ob = sel_mix["methods"][name]["operating"].get(str(budget))
        if oa is None or ob is None:
            out[name] = {"reachable": False, "H-none_reached": oa is not None, "H-mix_reached": ob is not None}
            continue
        out[name] = {"difference": "H-none − H-mix", "budget": budget, "seeds": len(seeds),
                     "H-none_cell": oa["cell"], "H-mix_cell": ob["cell"],
                     **ps.paired(_det_at(ra, name, oa["index"]), _det_at(rb, name, ob["index"]), W)}
    return out


def family_p(rows_none, rows_mix, sel_none, sel_mix, r4: dict, W) -> dict:
    """Family P: the price of haze at the primary budget, Holm across the methods (those computable)."""
    fam = price_of_haze(rows_none, rows_mix, sel_none, sel_mix, r4, W, r4["primary_budget"])
    pv = {k: v["p_wilcoxon"] for k, v in fam.items() if v.get("reachable", True)}
    for k, h in ps.holm(pv).items():
        fam[k].update(p_holm=h["p_holm"], reject=h["reject"])
    return fam


def floors_on_test(rows: list[dict], sel: dict, W) -> dict:
    """Descriptive — on a scenario's test seeds, every selected floor setting (floor, useful floor, both without
    r < 0.1): false incidents with seed-bootstrap intervals, pooled detection and validity there."""
    out = {}
    for name, prow in by_pipeline(rows).items():
        m = ps.seed_matrix(prow)
        pc = ps.pooled(m)
        vc = valid_cells(prow)
        res = {}
        for key in ("floor", "useful_floor", "floor_r_ge_0.1", "useful_floor_r_ge_0.1"):
            s = sel["methods"][name].get(key)
            if s is None:
                res[key] = None
                continue
            j = s["index"]
            res[key] = {"cell": m["grid"][j], "false_incidents": ps.fa_intervals(m, j, W), "det": _r(pc["det"][j]),
                        "valid_here": None if vc is None else vc[j]}
        caps = np.array([r["at_cap_by_target"] for r in prow], dtype=float)
        targets = sorted({_target(c) for c in m["grid"]})
        res["share_capped_by_target"] = {f"{t:g}": _r(caps[:, i].mean()) for i, t in enumerate(targets)}
        out[name] = res
    return out


def dose_response(scen_rows: dict, sels: dict, r4: dict, seeds_max: int) -> dict:
    """Descriptive (§6.4) — on the shared seeds ≤ seeds_max: detection at 1 and 3 a month in the deployment view
    (each scenario's selection: its own for H-none and H-mix, H-mix's for the dose points) and at equal false alarms,
    and the pooled floor of every method."""
    out = {}
    for sc, rows in scen_rows.items():
        rows = [r for r in rows if r["seed"] <= seeds_max]
        if not rows:
            continue
        sel = sels.get(sc, sels["H-mix"])
        res = {"seeds": len(rows), "selection_from": sc if sc in sels else "H-mix", "methods": {}}
        for name, prow in by_pipeline(rows).items():
            m = ps.seed_matrix(prow)
            pc = ps.pooled(m)
            d = {}
            for b in (1, 3):
                o = sel["methods"][name]["operating"].get(str(b))
                d[f"det_at_{b}"] = None if o is None else _r(pc["det"][o["index"]])
                d[f"fa_at_{b}"] = None if o is None else _r(pc["fa"][o["index"]])
                d[f"det_at_equal_fa_{b}"] = _r(det_at_equal_fa(pc["fa"], pc["det"], b))
            j = int(np.lexsort((np.arange(len(pc["fa"])), -pc["det"], pc["fa"]))[0])
            d["own_floor"] = {"cell": m["grid"][j], "fa_per_month": _r(pc["fa"][j]), "det": _r(pc["det"][j])}
            res["methods"][name] = d
        out[sc] = res
    return out


def write_analysis_r4(r4: dict, out: Path, selection_only: bool = False) -> list:
    out = Path(out)
    sels, sel_rows = {}, {}
    for sc in r4["contrast"]:
        rows = load_stage(out, "selection", sc, r4.get("round", "r4"))
        if not rows:
            raise FileNotFoundError(f"no selection seeds under {out}/r4/selection/{sc}")
        sel_rows[sc], sels[sc] = rows, selection_r4(rows, r4)
    meta = {"label": "SIMULATION", "protocol": "docs/research/protocol-r4.md (R4)", "base": r4["base"],
            "budgets": r4["budgets"], "methods": r4["methods"], "contrast": r4["contrast"],
            "primary_budget": r4["primary_budget"], "useful_detection": r4["useful_detection"]}
    files = {"r4_selection.json": {**meta, "selection": sels,
                                   "selection_seeds": {sc: [r["seed"] for r in rows] for sc, rows in sel_rows.items()},
                                   "seed_tables": {sc: compact_r2(rows) for sc, rows in sel_rows.items()}}}
    if not selection_only:
        rng = make_rngs(int(r4["bootstrap"]["seed"]))["research"]
        test = {sc: load_stage(out, "test", sc, r4.get("round", "r4")) for sc in r4["scenarios"]}
        test = {sc: rows for sc, rows in test.items() if rows}
        none, mix = r4["contrast"]
        n = len(set(r["seed"] for r in test.get(none, [])) & set(r["seed"] for r in test.get(mix, [])))
        W = ps.resample_weights(n, int(r4["bootstrap"]["resamples"]), rng)
        analysis = {**meta, "selection": sels, "family_P": None, "descriptive": {}, "scenarios": {}}
        if n:
            analysis["family_P"] = family_p(test[none], test[mix], sels[none], sels[mix], r4, W)
            analysis["descriptive"]["price_by_budget"] = {
                str(b): price_of_haze(test[none], test[mix], sels[none], sels[mix], r4, W, b)
                for b in r4["budgets"] if b != r4["primary_budget"]}
            analysis["descriptive"]["price_at_equal_fa"] = {
                name: {str(b): _r(det_at_equal_fa(*_pooled_curve(test[none], name), b)
                                  - det_at_equal_fa(*_pooled_curve(test[mix], name), b)) for b in r4["budgets"]}
                for name in r4["methods"]}
        analysis["descriptive"]["dose_response"] = dose_response(test, sels, r4, seeds_max=6050)
        for sc, rows in test.items():
            sel = sels.get(sc, sels[mix])
            Ws = ps.resample_weights(len(rows), int(r4["bootstrap"]["resamples"]), rng)
            sc_cfg = r4["scenarios"][sc]
            analysis["scenarios"][sc] = {
                "role": sc_cfg["role"], "selection_from": sc if sc in sels else mix,
                "seeds": [r["seed"] for r in rows], "test_days_per_seed": rows[0]["test_days"],
                "complete": len(rows) == sc_cfg["seeds"]["test"]["to"] - sc_cfg["seeds"]["test"]["from"] + 1,
                "methods": scenario_results(rows, sel, r4, Ws), "floors": floors_on_test(rows, sel, Ws)}
        files["r4_test.json"] = {**meta, "scenarios": {sc: compact_r2(rows) for sc, rows in test.items()}}
        files["r4_analysis.json"] = analysis
    paths = []
    for fname, obj in files.items():
        write_text_atomic(out / fname, json.dumps(obj, indent=1, default=_json))
        paths.append(str(out / fname))
    return paths


def _pooled_curve(rows: list[dict], name: str):
    pc = ps.pooled(ps.seed_matrix(by_pipeline(rows)[name]))
    return pc["fa"], pc["det"]


def write_test_table_r4(r4: dict, out: Path) -> list:
    """The test stage's compact per-seed table (`r4_test.json`, as R2/R3: per scenario and method, the per-seed false
    incidents and detections at every cell), written without computing any endpoint. Used to log the runs while the
    analysis waits (protocol R4 §10)."""
    out = Path(out)
    test = {sc: load_stage(out, "test", sc, r4.get("round", "r4")) for sc in r4["scenarios"]}
    meta = {"label": "SIMULATION", "protocol": "docs/research/protocol-r4.md (R4)", "base": r4["base"],
            "methods": r4["methods"], "seeds": {sc: [r["seed"] for r in rows] for sc, rows in test.items()}}
    obj = {**meta, "scenarios": {sc: compact_r2(rows) for sc, rows in test.items() if rows}}
    write_text_atomic(out / "r4_test.json", json.dumps(obj, indent=1, default=_json))
    return [str(out / "r4_test.json")]

