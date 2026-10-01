"""Protocol R2 analysis rules (§4–§5, §10) on synthetic seed files: floor knob and operating point with their tie
rules, B*, the Pareto front and equal-FA interpolation, the E3 decomposition, E5 split, families F and D."""
import json

import pytest

from prahari.research.analysis_r2 import (det_at_equal_fa, floor_index, op_index, pareto_front, write_analysis_r2)

METHODS = ["P2", "P2-med", "P2-medSCMR", "P2-factor", "P2-gate", "Mei", "Mei-med", "AR"]


def test_floor_and_operating_tie_rules():
    fa, det = [5.0, 2.0, 2.0, 9.0], [0.9, 0.5, 0.6, 0.95]
    assert floor_index(fa, det) == 2                       # lowest FA; tie broken by higher detection
    assert op_index(fa, det, 5.0) == 0 and op_index(fa, det, 1.0) is None
    assert op_index([1.0, 0.5], [0.7, 0.7], 3) == 1         # equal detection: lower FA


def test_pareto_and_equal_fa():
    fa, det = [1.0, 2.0, 3.0, 10.0], [0.5, 0.4, 0.8, 0.9]
    assert pareto_front(fa, det) == [0, 2, 3]
    assert det_at_equal_fa(fa, det, 3.0) == pytest.approx(0.8) and det_at_equal_fa(fa, det, 0.5) == 0.0


def _row(seed, fi, lat, starts):
    """A seed with two cells per method: cell 0 strict, cell 1 permissive; one haze episode 40 000–41 000 min."""
    pipes = {m: {"knob": "target", "grid": [1.0, 3.0], "false_incidents": fi, "latencies": lat,
                 "fi_starts": starts} for m in METHODS}
    pipes["P2-med"] = {**pipes["P2"], "false_incidents": [0, fi[1]], "fi_starts": [[], starts[1]]}
    return {"seed": seed, "test_days": 30, "n_fires": 2, "degraded": [], "haze_episodes": [[40000, 41000, 1.0]],
            "fires_haze_overlap": [True, False], "pipelines": pipes}


def test_end_to_end(tmp_path):
    r2 = {"base": "x", "budgets": [1, 3, 10, 30], "compared": METHODS[:-1], "family_F": ["P2-med"],
          "family_D": ["P2-med"], "bootstrap": {"seed": 1, "resamples": 200},
          "scenarios": {"H-mix": {"role": "primary", "seeds": {"test": {"from": 1, "to": 6}}}}}
    for stage, seeds in (("selection", range(1, 4)), ("test", range(1, 7))):
        d = tmp_path / "r2" / stage / "H-mix"
        d.mkdir(parents=True)
        for s in seeds:
            # cell 0: 2 false incidents a month (one inside haze), fires 1/2 detected; cell 1: 8 a month, both detected
            row = _row(s, [2, 8], [[10, None], [5, 7]], [[40500, 50000], [50000] * 8])
            (d / f"seed{s}.json").write_text(json.dumps(row))
    write_analysis_r2(r2, tmp_path)
    a = json.loads((tmp_path / "r2_analysis.json").read_text())
    assert a["b_star"] == 3                                  # every compared method reaches 3/month at cell 0
    p2 = a["scenarios"]["H-mix"]["methods"]["P2"]
    assert p2["floor_at_selected_knob"]["cell"] == 1.0
    dec = p2["floor_at_selected_knob"]["decomposition"]
    assert (dec["total"], dec["inside"], dec["outside"]) == (2.0, 1.0, 1.0)
    assert p2["at_b_star"]["by_haze_overlap"]["overlap"]["det"] == 1.0
    assert p2["at_b_star"]["by_haze_overlap"]["no_overlap"]["det"] == 0.0
    assert p2["at_b_star"]["mean_ttc_min"] == pytest.approx(95.0)       # (10 + 180) / 2
    fam = a["scenarios"]["H-mix"]["families"]
    assert fam["F"]["P2-med"]["mean_diff"] == pytest.approx(-2.0)        # P2-med floor 0 vs P2 2 per month
    assert fam["D"]["P2-med"]["reachable"] and fam["D"]["P2-med"]["mean_diff"] == pytest.approx(0.0)
    assert a["scenarios"]["H-mix"]["complete"]
