"""Protocol R3 analysis (docs/research/protocol-r3.md): median + SCMR (P2-medSCMR) against the evidence gate
(P2-gate), head to head, with P2 as a reference.

Selection on the H-mix selection seeds uses valid settings only (the R2-D1 rule, registered in R3 from the start): the
floor setting, every budget's operating point, and B* — the smallest of {1, 3, 10, 30} a month both compared methods
reach. On the H-mix test seeds: H1 (per-seed detection at B*) and H2 (per-seed false incidents per month at the floor
settings), differences P2-medSCMR − P2-gate, two-sided Wilcoxon with a paired seed-bootstrap interval, Holm across
{H1, H2}. Everything else is descriptive. Writes `r3_selection.json`, `r3_test.json`, `r3_analysis.json`. All SIM.
"""
from __future__ import annotations

import json
from pathlib import Path

from prahari.core.rng import make_rngs
from prahari.record.writer import write_text_atomic
from prahari.research import pstats as ps
from prahari.research.analysis import _json, _r, by_pipeline
from prahari.research.analysis_r2 import _per_seed_fa, compact_r2, scenario_results, selection_r2


def load_stage(out: Path, stage: str, scenario: str, round_name: str = "r3") -> list[dict]:
    files = sorted((Path(out) / round_name / stage / scenario).glob("seed*.json"), key=lambda f: int(f.stem[4:]))
    return [json.loads(f.read_text(encoding="utf-8")) for f in files]


def _pair(a, b, W) -> dict:
    return {"difference": "P2-medSCMR − P2-gate", **ps.paired(a, b, W)}


def head_to_head(rows: list[dict], sel: dict, r3: dict, W) -> dict:
    """H1 and H2 (Holm across both), plus the descriptive comparison at every budget both methods reach."""
    x, y = r3["compared"]
    mats = {k: ps.seed_matrix(v) for k, v in by_pipeline(rows).items()}
    s, b = sel["methods"], sel["b_star"]
    out, pv = {}, {}
    if b is not None:
        jx, jy = s[x]["operating"][str(b)]["index"], s[y]["operating"][str(b)]["index"]
        out["H1_detection_at_b_star"] = {"budget": b, **_pair(ps.per_seed_det(mats[x], jx), ps.per_seed_det(mats[y], jy), W)}
        pv["H1_detection_at_b_star"] = out["H1_detection_at_b_star"]["p_wilcoxon"]
    else:
        out["H1_detection_at_b_star"] = {"reachable": False}
    if s[x]["floor"] and s[y]["floor"]:
        out["H2_floor"] = _pair(_per_seed_fa(mats[x], s[x]["floor"]["index"]), _per_seed_fa(mats[y], s[y]["floor"]["index"]), W)
        pv["H2_floor"] = out["H2_floor"]["p_wilcoxon"]
    else:
        out["H2_floor"] = {"reachable": False}
    for k, h in ps.holm(pv).items():
        out[k].update(p_holm=h["p_holm"], reject=h["reject"])
    desc = {}
    for bb in r3["budgets"]:
        ox, oy = s[x]["operating"][str(bb)], s[y]["operating"][str(bb)]
        if ox is None or oy is None:
            desc[str(bb)] = {"reachable": False}
            continue
        px, py = ps.pooled(mats[x]), ps.pooled(mats[y])
        desc[str(bb)] = {"reachable": True, x: {"det": _r(px["det"][ox["index"]]), "fa_per_month": _r(px["fa"][ox["index"]])},
                         y: {"det": _r(py["det"][oy["index"]]), "fa_per_month": _r(py["fa"][oy["index"]])},
                         "paired": _pair(ps.per_seed_det(mats[x], ox["index"]), ps.per_seed_det(mats[y], oy["index"]), W)}
    out["descriptive_by_budget"] = desc
    return out


def write_analysis_r3(r3: dict, out: Path) -> list:
    out = Path(out)
    sel_rows = load_stage(out, "selection", "H-mix")
    if not sel_rows:
        raise FileNotFoundError("no H-mix selection seeds under results/research/r3/selection/H-mix")
    sel = selection_r2(sel_rows, r3, validity=True)                  # R3: the validity rule is registered
    meta = {"label": "SIMULATION", "protocol": "docs/research/protocol-r3.md (R3)", "base": r3["base"],
            "budgets": r3["budgets"], "compared": r3["compared"], "reference": r3["reference"],
            "selection_seeds": [r["seed"] for r in sel_rows]}
    files = {"r3_selection.json": {**meta, "selection": sel, **compact_r2(sel_rows)}}
    analysis = {**meta, "b_star": sel["b_star"], "selection": sel, "scenarios": {}}
    tests = {}
    for name, sc in r3["scenarios"].items():
        rows = load_stage(out, "test", name)
        if not rows:
            continue
        rng = make_rngs(int(r3["bootstrap"]["seed"]))["research"]
        W = ps.resample_weights(len(rows), int(r3["bootstrap"]["resamples"]), rng)
        res = {"role": sc["role"], "seeds": [r["seed"] for r in rows], "test_days_per_seed": rows[0]["test_days"],
               "complete": len(rows) == len(range(sc["seeds"]["test"]["from"], sc["seeds"]["test"]["to"] + 1)),
               "methods": scenario_results(rows, sel, r3, W),
               "head_to_head": head_to_head(rows, sel, r3, W)}
        if name != "H-mix":
            res["head_to_head"]["note"] = "descriptive (secondary scenario); the confirmatory tests are on H-mix"
        analysis["scenarios"][name] = res
        tests[name] = compact_r2(rows)
    files["r3_test.json"] = {**meta, "scenarios": tests}
    files["r3_analysis.json"] = analysis
    paths = []
    for fname, obj in files.items():
        write_text_atomic(out / fname, json.dumps(obj, indent=1, default=_json))
        paths.append(str(out / fname))
    return paths
