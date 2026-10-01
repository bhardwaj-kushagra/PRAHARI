"""Protocol R2 analysis (docs/research/protocol-r2.md §4–§5, §10): B*, the floor knob and operating points chosen on
the H-mix selection seeds; E1–E5 and the Holm families F and D on the H-mix test seeds; the deployment and
equal-false-alarm views of every secondary scenario. Writes `r2_selection.json`, `r2_test.json` and
`r2_analysis.json` (results/research/), the only inputs of R2's tables and figures (charter rule 4). All SIM.

Equal-false-alarm view (R8's rule on a knob surface): detection at budget x is interpolated, linear in log₁₀ FA, along
the method's Pareto front (the cells no other cell beats on both false incidents and detection), which is the curve
itself for a one-knob method with a monotone curve.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from prahari.core.rng import make_rngs
from prahari.record.writer import write_text_atomic
from prahari.research import pstats as ps
from prahari.research.analysis import _json, _r, by_pipeline
from prahari.research.hazesplit import PAD_MIN, active_mask

MISS_MIN = 180                                  # E4 — a missed fire counts as 180 min
INVALID_INCIDENT_MIN = 1440                     # DECISIONS R2-D1 — a false incident lasting ≥ 24 h: continuous alarming


def load_r2_stage(out: Path, stage: str, scenario: str) -> list[dict]:
    files = sorted((Path(out) / "r2" / stage / scenario).glob("seed*.json"), key=lambda f: int(f.stem[4:]))
    return [json.loads(f.read_text(encoding="utf-8")) for f in files]


def floor_index(fa, det, allowed=None):
    """§10.10 — the lowest pooled false incidents; ties: higher detection, then the first cell. `allowed` (R2-D1
    sensitivity) restricts the cells; None when no cell is allowed."""
    cells = [j for j in range(len(fa)) if allowed is None or allowed[j]]
    return int(min(cells, key=lambda j: (fa[j], -det[j], j))) if cells else None


def op_index(fa, det, budget: float, allowed=None):
    """§10.10 — the highest detection among cells with pooled false incidents ≤ budget; ties: lower false incidents,
    then the first cell (None when no cell meets the budget). `allowed` as in `floor_index`."""
    ok = [j for j in range(len(fa)) if fa[j] <= budget and (allowed is None or allowed[j])]
    return int(min(ok, key=lambda j: (-det[j], fa[j], j))) if ok else None


def valid_cells(prow: list[dict]):
    """DECISIONS R2-D1 — a cell is valid when no seed has a false incident lasting ≥ 24 h (continuous alarming makes
    M46's incident count meaningless). None when the seed files lack the field."""
    if not all("fi_longest_min" in r for r in prow):
        return None
    K = len(prow[0]["fi_longest_min"])
    return [all(r["fi_longest_min"][j] < INVALID_INCIDENT_MIN for r in prow) for j in range(K)]


def pareto_front(fa, det) -> list[int]:
    """Cells not beaten on both false incidents (lower) and detection (higher), sorted by false incidents."""
    order = sorted(range(len(fa)), key=lambda j: (fa[j], -det[j], j))
    front, best = [], -1.0
    for j in order:
        if det[j] > best:
            front.append(j)
            best = det[j]
    return front


def det_at_equal_fa(fa, det, x: float) -> float:
    """R8 along the Pareto front: detection at false-incident rate x (0 below the floor)."""
    f = pareto_front(fa, det)
    return ps.interp_det(np.asarray(fa)[f], np.asarray(det)[f], x)


def mean_ttc(prow: list[dict], j: int) -> float | None:
    """E4 — mean time to confirmation at cell j, pooled over fires, a miss counting as 180 min."""
    lat = [MISS_MIN if v is None else v for r in prow for v in r["latencies"][j]]
    return float(np.mean(lat)) if lat else None


def selection_r2(rows: list[dict], r2: dict, validity: bool = False) -> dict:
    """§4 — per method: the floor knob, every budget's operating point, and B*. With `validity`, the R2-D1
    sensitivity: only cells valid on these seeds may be chosen."""
    P = by_pipeline(rows)
    out = {"methods": {}, "rule": "R2-D1 validity (no false incident ≥ 24 h on any seed)" if validity else "registered"}
    for name, prow in P.items():
        m = ps.seed_matrix(prow)
        pc = ps.pooled(m)
        allowed = valid_cells(prow) if validity else None
        jf = floor_index(pc["fa"], pc["det"], allowed)
        ops = {}
        for b in r2["budgets"]:
            j = op_index(pc["fa"], pc["det"], b, allowed)
            ops[str(b)] = None if j is None else {"index": j, "cell": m["grid"][j], "fa_per_month": _r(pc["fa"][j]),
                                                  "det": _r(pc["det"][j])}
        vc = valid_cells(prow)
        out["methods"][name] = {"knob": m["knob"], "operating": ops,
                                "floor": None if jf is None else {"index": jf, "cell": m["grid"][jf],
                                                                  "fa_per_month": _r(pc["fa"][jf]), "det": _r(pc["det"][jf])},
                                "invalid_cells": None if vc is None else [m["grid"][j] for j, ok in enumerate(vc) if not ok]}
    reach = [b for b in r2["budgets"] if all(out["methods"][x]["operating"][str(b)] is not None for x in r2["compared"])]
    out["b_star"] = reach[0] if reach else None
    return out


def _per_seed_fa(m: dict, j: int) -> np.ndarray:
    return m["F"][:, j] / m["days"] * 30.0


def decomposition(prow: list[dict], rows: list[dict], j: int) -> dict:
    """E3 — false incidents at cell j starting inside haze (an episode active at the first alarm), outside, and
    inside with the 60-minute padding (R2-10's tags), per month."""
    days = sum(r["test_days"] for r in rows)
    n_in = n_pad = n_all = 0
    for r, row in zip(rows, prow):
        T = (r["test_days"] + 28) * 1440
        act, pad = active_mask(r["haze_episodes"], T), active_mask(r["haze_episodes"], T, PAD_MIN)
        starts = row["fi_starts"][j]
        n_all += len(starts)
        n_in += sum(bool(act[t]) for t in starts)
        n_pad += sum(bool(pad[t]) for t in starts)
    rate = lambda k: _r(k / days * 30.0)                                        # noqa: E731
    return {"total": rate(n_all), "inside": rate(n_in), "outside": rate(n_all - n_in), "inside_padded": rate(n_pad),
            "outside_padded": rate(n_all - n_pad), "count": n_all, "count_inside": n_in, "count_inside_padded": n_pad,
            "share_inside": _r(n_in / n_all) if n_all else None}


def by_overlap(prow: list[dict], rows: list[dict], j: int) -> dict:
    """E5 — detection at cell j for fires whose first 3 h overlap haze, and for the others."""
    hit = {True: [0, 0], False: [0, 0]}
    for r, row in zip(rows, prow):
        for lat, ov in zip(row["latencies"][j], r["fires_haze_overlap"]):
            hit[bool(ov)][0] += lat is not None
            hit[bool(ov)][1] += 1
    return {k: {"detected": d, "fires": n, "det": _r(d / n) if n else None}
            for k, (d, n) in (("overlap", hit[True]), ("no_overlap", hit[False]))}


def scenario_results(rows: list[dict], sel: dict, r2: dict, W) -> dict:
    """Per method on one scenario's seeds: E1 (own floor and the H-mix floor knob), E2 at B*, E3, E4 and E5."""
    b = sel["b_star"]
    out = {}
    for name, prow in by_pipeline(rows).items():
        m = ps.seed_matrix(prow)
        pc, bc = ps.pooled(m), ps.boot_curve(m, W)
        s = sel["methods"][name]
        jf = s["floor"]["index"] if s["floor"] else None
        jo = (s["operating"].get(str(b)) or {}).get("index") if b is not None else None
        own = floor_index(pc["fa"], pc["det"])
        vc = valid_cells(prow)
        res = {"knob": m["knob"],
               "floor_at_selected_knob": None if jf is None else {
                   "cell": m["grid"][jf], "false_incidents": ps.fa_intervals(m, jf, W), "det": _r(pc["det"][jf]),
                   "decomposition": decomposition(prow, rows, jf), "valid_here": None if vc is None else vc[jf]},
               "own_floor": {"cell": m["grid"][own], "fa_per_month": _r(pc["fa"][own]), "det": _r(pc["det"][own])},
               "det_at_equal_fa": {str(x): _r(det_at_equal_fa(pc["fa"], pc["det"], x)) for x in r2["budgets"]},
               "amoc": [{"cell": m["grid"][j], "fa_per_month": _r(pc["fa"][j]), "det": _r(pc["det"][j]),
                         "mean_ttc_min": _r(mean_ttc(prow, j), 2)} for j in range(len(m["grid"]))],
               "pareto": pareto_front(pc["fa"], pc["det"])}
        if jo is not None:
            lat = [v for r in prow for v in r["latencies"][jo] if v is not None]
            res["at_b_star"] = {"cell": m["grid"][jo], "false_incidents": ps.fa_intervals(m, jo, W),
                                "det": _r(pc["det"][jo]), "det_ci95": [_r(v) for v in bc["det_ci"][jo]],
                                "detected": int(m["D"][:, jo].sum()), "fires": int(m["n"].sum()),
                                "latency_median_min": _r(np.median(lat), 1) if lat else None,
                                "mean_ttc_min": _r(mean_ttc(prow, jo), 2), "by_haze_overlap": by_overlap(prow, rows, jo),
                                "valid_here": None if vc is None else vc[jo]}
        out[name] = res
    return out


def families_r2(rows: list[dict], sel: dict, r2: dict, W) -> dict:
    """Family F (per-seed false incidents per month at the floor knobs) and family D (per-seed detection at B*), each
    method against P2, two-sided Wilcoxon with Holm's correction; differences are method − P2."""
    mats = {k: ps.seed_matrix(v) for k, v in by_pipeline(rows).items()}
    s, b = sel["methods"], sel["b_star"]
    out = {}
    for fam, names in (("F", r2["family_F"]), ("D", r2["family_D"])):
        comps, pv = {}, {}
        for x in names:
            if fam == "F":
                if s[x]["floor"] is None or s["P2"]["floor"] is None:
                    comps[x] = {"reachable": False}
                    continue
                a, c = _per_seed_fa(mats[x], s[x]["floor"]["index"]), _per_seed_fa(mats["P2"], s["P2"]["floor"]["index"])
            else:
                if b is None or s[x]["operating"][str(b)] is None or s["P2"]["operating"][str(b)] is None:
                    comps[x] = {"reachable": False}
                    continue
                a = ps.per_seed_det(mats[x], s[x]["operating"][str(b)]["index"])
                c = ps.per_seed_det(mats["P2"], s["P2"]["operating"][str(b)]["index"])
            comps[x] = {"reachable": True, "difference": "method − P2", **ps.paired(a, c, W)}
            pv[x] = comps[x]["p_wilcoxon"]
        for x, h in ps.holm(pv).items():
            comps[x].update(p_holm=h["p_holm"], reject=h["reject"])
        out[fam] = comps
    return out


def compact_r2(rows: list[dict]) -> dict:
    out = {"seeds": [r["seed"] for r in rows], "n_fires": [r["n_fires"] for r in rows],
           "degraded": sorted({d for r in rows for d in r["degraded"]}), "pipelines": {}}
    for name, prow in by_pipeline(rows).items():
        m = ps.seed_matrix(prow)
        out["pipelines"][name] = {"knob": m["knob"], "grid": m["grid"], "false_incidents": m["F"].astype(int).tolist(),
                                  "detected": m["D"].astype(int).tolist()}
    return out


def write_analysis_r2(r2: dict, out: Path) -> list:
    out = Path(out)
    sel_rows = load_r2_stage(out, "selection", "H-mix")
    if not sel_rows:
        raise FileNotFoundError("no H-mix selection seeds under results/research/r2/selection/H-mix")
    sel = selection_r2(sel_rows, r2)
    sel_v = selection_r2(sel_rows, r2, validity=True)                  # DECISIONS R2-D1 sensitivity
    meta = {"label": "SIMULATION", "protocol": "docs/research/protocol-r2.md (R2)", "base": r2["base"],
            "budgets": r2["budgets"], "selection_seeds": [r["seed"] for r in sel_rows]}
    files = {"r2_selection.json": {**meta, "selection": sel, "selection_R2_D1": sel_v, **compact_r2(sel_rows)}}
    analysis = {**meta, "b_star": sel["b_star"], "selection": sel, "b_star_R2_D1": sel_v["b_star"],
                "selection_R2_D1": sel_v, "scenarios": {}}
    tests = {}
    for name, sc in r2["scenarios"].items():
        rows = load_r2_stage(out, "test", name)
        if not rows:
            continue
        rng = make_rngs(int(r2["bootstrap"]["seed"]))["research"]
        W = ps.resample_weights(len(rows), int(r2["bootstrap"]["resamples"]), rng)
        res = {"role": sc["role"], "seeds": [r["seed"] for r in rows], "test_days_per_seed": rows[0]["test_days"],
               "complete": len(rows) == len(range(sc["seeds"]["test"]["from"], sc["seeds"]["test"]["to"] + 1)),
               "methods": scenario_results(rows, sel, r2, W)}
        if name == "H-mix":
            res["families"] = families_r2(rows, sel, r2, W)
        res["sensitivity_R2_D1"] = {"methods": scenario_results(rows, sel_v, r2, W)}
        if name == "H-mix":
            res["sensitivity_R2_D1"]["families"] = families_r2(rows, sel_v, r2, W)
        analysis["scenarios"][name] = res
        tests[name] = compact_r2(rows)
    files["r2_test.json"] = {**meta, "scenarios": tests}
    files["r2_analysis.json"] = analysis
    paths = []
    for fname, obj in files.items():
        write_text_atomic(out / fname, json.dumps(obj, indent=1, default=_json))
        paths.append(str(out / fname))
    return paths
