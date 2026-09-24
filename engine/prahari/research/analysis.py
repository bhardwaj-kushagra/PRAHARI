"""Protocol R1 analysis: operating points chosen on the selection seeds, every reported number on the test seeds,
and the sensitivity sweeps. Writes `r1_selection.json`, `r1_test.json`, `r1_sweeps.json` and `r1_analysis.json`
(results/research/), the only inputs of the paper's tables and figures (CLAUDE.md rule 10)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from prahari.core.rng import make_rngs
from prahari.record.writer import write_text_atomic
from prahari.research import pstats as ps

FAMILY_A = ["P0", "P1", "P1t", "AR"]
FAMILY_B = ["P2-SCMR", "P2-Q2", "P2-Q3", "P2-med", "P2-QCC", "P2-TTC"]


def load_stage(out: Path, stage: str) -> list[dict]:
    """Per-seed rows of a stage, in seed order."""
    files = sorted((out / stage).glob("seed*.json"), key=lambda f: int(f.stem[4:]))
    return [json.loads(f.read_text(encoding="utf-8")) for f in files]


def by_pipeline(rows: list[dict]) -> dict:
    """{pipeline: [its row per seed]} (seeds in the same order for every pipeline: paired)."""
    return {name: [{**r["pipelines"][name], "test_days": r["test_days"]} for r in rows] for name in rows[0]["pipelines"]}


def _r(v, nd=4):
    return None if v is None else round(float(v), nd)


def compact(rows: list[dict]) -> dict:
    """The committed per-seed counts: per pipeline and knob, false incidents, detected and fires per seed."""
    out = {"seeds": [r["seed"] for r in rows], "n_fires": [r["n_fires"] for r in rows], "pipelines": {}}
    for name, prow in by_pipeline(rows).items():
        m = ps.seed_matrix(prow)
        out["pipelines"][name] = {"knob": m["knob"], "grid": m["grid"], "false_incidents": m["F"].astype(int).tolist(),
                                  "detected": m["D"].astype(int).tolist(), "h": [r.get("h") for r in prow]}
    return out


def selection(sel_rows: list[dict], budgets) -> dict:
    """R4 — the selected knob index per pipeline and budget, with the selection seeds' pooled rate there."""
    out = {}
    for name, prow in by_pipeline(sel_rows).items():
        m = ps.seed_matrix(prow)
        fa = ps.pooled(m)["fa"]
        out[name] = {}
        for b in budgets:
            j = ps.select(m, b)
            out[name][str(b)] = {"index": j, "knob": m["knob"], "value": None if j is None else m["grid"][j],
                                 "selection_fa_per_month": None if j is None else _r(fa[j])}
    return out


def test_results(test_rows: list[dict], sel: dict, r1: dict, W) -> dict:
    """Curves, pAUC and the budget points (FA with Poisson and bootstrap intervals, detection, latency, time to
    confirmation) for every pipeline on the test seeds."""
    lo, hi = r1["pauc_range"]
    out = {}
    for name, prow in by_pipeline(test_rows).items():
        m = ps.seed_matrix(prow)
        pc, bc = ps.pooled(m), ps.boot_curve(m, W)
        curve = [{"knob": m["grid"][j], "fa_per_month": _r(pc["fa"][j]), "fa_ci95": [_r(v) for v in bc["fa_ci"][j]],
                  "det": _r(pc["det"][j]), "det_ci95": [_r(v) for v in bc["det_ci"][j]]} for j in range(len(m["grid"]))]
        boot_pauc = [ps.pauc(f, d, lo, hi) for f, d in zip(*_boot_points(m, W[:1000]))]
        res = {"knob": m["knob"], "curve": curve, "pauc": _r(ps.pauc(pc["fa"], pc["det"], lo, hi)),
               "pauc_ci95": [_r(v) for v in np.percentile(boot_pauc, [2.5, 97.5])], "at_budget": {}}
        for b in r1["budgets"]:
            j = sel.get(name, {}).get(str(b), {}).get("index")
            if j is None:
                res["at_budget"][str(b)] = {"reachable": False}
                continue
            lat = [v for r in prow for v in r["latencies"][j] if v is not None]
            det = pc["det"][j]
            res["at_budget"][str(b)] = {"reachable": True, "knob": m["grid"][j],
                                        "false_incidents": ps.fa_intervals(m, j, W),
                                        "det": _r(det), "det_ci95": [_r(v) for v in bc["det_ci"][j]],
                                        "detected": int(m["D"][:, j].sum()), "fires": int(m["n"].sum()),
                                        "latency_median_min": _r(np.median(lat), 1) if lat else None,
                                        "time_to_confirm": ps.time_to_confirm(prow, j)}
        out[name] = res
    return out


def _boot_points(m: dict, W):
    fa = (W @ m["F"]) / (W @ m["days"])[:, None] * 30.0
    det = (W @ m["D"]) / (W @ m["n"])[:, None]
    return fa, det


def families(test_rows: list[dict], sel: dict, budget: float, W) -> dict:
    """R6, R7 — P2 against each pipeline of family A (baselines) and family B (ablations) at the budget's knobs."""
    P = by_pipeline(test_rows)
    mats = {k: ps.seed_matrix(v) for k, v in P.items()}
    j2 = sel["P2"][str(budget)]["index"]
    out = {}
    for fam, names in (("A", FAMILY_A), ("B", FAMILY_B)):
        comps, pv = {}, {}
        for x in names:
            jx = sel[x][str(budget)]["index"]
            if jx is None or j2 is None:
                comps[x] = {"reachable": False}
                continue
            c = ps.paired(ps.per_seed_det(mats["P2"], j2), ps.per_seed_det(mats[x], jx), W)
            comps[x] = {"reachable": True, **c}
            pv[x] = c["p_wilcoxon"]
        for x, h in ps.holm(pv).items():
            comps[x].update(p_holm=h["p_holm"], reject=h["reject"])
        out[fam] = comps
    return out


def priors(test_rows: list[dict], sel: dict, r1: dict) -> dict:
    """Wrong-prior sweep: P2 with day types flipped, per budget at P2's selected knob and at equal FA (interpolated)."""
    P = by_pipeline(test_rows)
    out = {}
    for name in ["P2", *[f"P2-prior{q:g}" for q in r1["priors"]]]:
        out[name] = _at_budgets(ps.seed_matrix(P[name]), sel["P2"], r1["budgets"])
    return out


def _at_budgets(m: dict, sel_p: dict, budgets) -> dict:
    """Per budget: FA and detection at the selected knob of `sel_p` (None if unreachable) and detection at that FA
    interpolated from the curve itself (R8 rule)."""
    pc = ps.pooled(m)
    out = {}
    for b in budgets:
        j = sel_p[str(b)]["index"]
        out[str(b)] = {"at_selected_knob": None if j is None else {"fa_per_month": _r(pc["fa"][j]),
                                                                   "det": _r(pc["det"][j])},
                       "det_at_equal_fa": _r(ps.interp_det(pc["fa"], pc["det"], b))}
    return out


def sweeps(out: Path, sel: dict, test_rows: list[dict], r1: dict) -> dict:
    """Protocol R1 §5 — per sweep point, pipeline and budget: (a) FA and detection at the knob selected on the default
    model, (b) detection at that budget interpolated from the point's own curve; the default point is the test
    stage's first ten seeds."""
    seeds = set(range(r1["seeds"]["sweep"]["from"], r1["seeds"]["sweep"]["to"] + 1))
    groups = {"default": [r for r in test_rows if r["seed"] in seeds]}
    for f in sorted((out / "sweeps").glob("*_seed*.json")):
        groups.setdefault(f.stem.rsplit("_seed", 1)[0], []).append(json.loads(f.read_text(encoding="utf-8")))
    res = {}
    for label, rows in groups.items():
        rows = sorted(rows, key=lambda r: r["seed"])
        res[label] = {"seeds": [r["seed"] for r in rows], "pipelines": {}}
        for name, prow in by_pipeline(rows).items():
            if name.startswith("P2-prior") or name not in sel:
                continue
            m = ps.seed_matrix(prow)
            pc = ps.pooled(m)
            res[label]["pipelines"][name] = {**_at_budgets(m, sel[name], r1["budgets"]),
                                             "fa_at_first_knob": _r(pc["fa"][0]), "det_at_first_knob": _r(pc["det"][0])}
    return res


def write_analysis(r1: dict, out: Path) -> list:
    """Build and write the four R1 result files; returns their paths."""
    out = Path(out)
    sel_rows, test_rows = load_stage(out, "selection"), load_stage(out, "test")
    sel = selection(sel_rows, r1["budgets"])
    rng = make_rngs(int(r1["bootstrap"]["seed"]))["research"]
    W = ps.resample_weights(len(test_rows), int(r1["bootstrap"]["resamples"]), rng)
    meta = {"label": "SIMULATION", "protocol": "docs/research/protocol.md (R1)", "base": r1["base"],
            "selection_seeds": [r["seed"] for r in sel_rows], "test_seeds": [r["seed"] for r in test_rows],
            "test_days_per_seed": test_rows[0]["test_days"] if test_rows else None, "budgets": r1["budgets"]}
    analysis = {**meta, "selection": sel, "test": test_results(test_rows, sel, r1, W),
                "comparisons": {str(b): families(test_rows, sel, b, W) for b in r1["budgets"]},
                "priors": priors(test_rows, sel, r1)}
    files = {"r1_selection.json": {**meta, **compact(sel_rows)}, "r1_test.json": {**meta, **compact(test_rows)},
             "r1_analysis.json": analysis}
    if (out / "sweeps").is_dir():
        files["r1_sweeps.json"] = {**meta, "sweeps": sweeps(out, sel, test_rows, r1)}
    paths = []
    for name, obj in files.items():
        write_text_atomic(out / name, json.dumps(obj, indent=1, default=_json))
        paths.append(str(out / name))
    return paths


def _json(o):
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))
