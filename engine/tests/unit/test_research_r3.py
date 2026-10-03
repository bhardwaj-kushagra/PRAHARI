"""Protocol R3: the method-subset evaluation equals the registered R2 evaluation cell for cell (fidelity), and the R3
head-to-head analysis (validity-restricted selection, B* over the compared pair, H1/H2 with Holm) on synthetic seeds."""
import json

import pytest

from prahari.core.config import load_config
from prahari.research.analysis_r3 import write_analysis_r3
from prahari.research.operating_r2 import evaluate_seed_r2
from prahari.research.runner_r2 import load_r2

from ..conftest import REPO

R3_METHODS = ("P2", "P2-medSCMR", "P2-gate")


def short_cfg():
    cfg = load_config(REPO / "configs" / "experiments" / "golden.yaml")
    ev = cfg["params"]["evaluation"]
    ev["calibration_days"], ev["tuning_days"], ev["test_days"] = 2, 2, 4
    cfg["world"]["n_nodes"] = 36
    return cfg


def test_r3_config_reuses_r2_unchanged():
    r2, r3 = load_r2(), load_r2("configs/research/r3.yaml")
    assert r3["m20b"] == r2["m20b"] and r3["cap"] == r2["cap"] and r3["budgets"] == r2["budgets"]
    for k in ("node", "v1t", "rho", "theta", "gate_p", "gate_window_min"):
        assert r3["grids"][k] == r2["grids"][k]
    for sc in ("H-mix", "H-sync", "H-gain", "H-patch"):
        a = {k: v for k, v in r2["scenarios"][sc].items() if k != "seeds"}
        b = {k: v for k, v in r3["scenarios"][sc].items() if k != "seeds"}
        assert a == b
    used = set(range(11, 34))                                    # development seeds (golden presets 11–30, 33)
    r1 = load_r2("configs/research/r1.yaml")
    for st in r1["seeds"].values():
        used |= set(range(st["from"], st["to"] + 1))
    for sc in r2["scenarios"].values():
        for st in sc["seeds"].values():
            used |= set(range(st["from"], st["to"] + 1))
    for sc in r3["scenarios"].values():                          # fresh seeds: none used in R1, R2 or development
        for st in sc["seeds"].values():
            assert not used & set(range(st["from"], st["to"] + 1))


def test_subset_equals_full_r2_evaluation():
    g = {**load_r2()["grids"], "node": [1, 3], "v1t": [1], "rho": [0, 3], "theta": [0.1, None], "h_mei": [100]}
    full = evaluate_seed_r2(short_cfg(), 11, g, (5000.0, 22))
    sub = evaluate_seed_r2(short_cfg(), 11, g, (5000.0, 22), R3_METHODS)
    assert list(sub["pipelines"]) == list(R3_METHODS)
    for m in R3_METHODS:
        assert sub["pipelines"][m] == full["pipelines"][m], m
    for k in ("haze_episodes", "fires_haze_overlap", "n_fires", "test_days"):
        assert sub[k] == full[k]


def _row(seed, fx, fy, lat_x, lat_y):
    def pipe(fi, lat):
        return {"knob": "target", "grid": [1.0, 3.0], "false_incidents": fi, "latencies": lat,
                "fi_starts": [[100] * fi[0], [200] * fi[1]], "fi_longest_min": [60, 60], "n_alarms_quiet": [5, 9]}
    return {"seed": seed, "test_days": 30, "n_fires": 2, "degraded": [], "haze_episodes": [[0, 50, 1.0]],
            "fires_haze_overlap": [False, False],
            "pipelines": {"P2": pipe(fx, lat_x), "P2-medSCMR": pipe(fx, lat_x), "P2-gate": pipe(fy, lat_y)}}


def test_head_to_head_analysis(tmp_path):
    r3 = {**load_r2("configs/research/r3.yaml"), "bootstrap": {"seed": 1, "resamples": 200}}
    r3["scenarios"] = {"H-mix": {**r3["scenarios"]["H-mix"], "seeds": {"selection": {"from": 1, "to": 3},
                                                                       "test": {"from": 1, "to": 8}}}}
    for stage, seeds in (("selection", range(1, 4)), ("test", range(1, 9))):
        d = tmp_path / "r3" / stage / "H-mix"
        d.mkdir(parents=True)
        for s in seeds:
            # medSCMR: 2 FI/month at cell 0, detects both fires; gate: 1 FI/month at cell 0, detects one
            row = _row(s, [2, 9], [1, 6], [[10, 20], [5, 6]], [[10, None], [5, 6]])
            (d / f"seed{s}.json").write_text(json.dumps(row))
    write_analysis_r3(r3, tmp_path)
    a = json.loads((tmp_path / "r3_analysis.json").read_text())
    assert a["b_star"] == 3                                      # both reach 3 a month at cell 0
    h = a["scenarios"]["H-mix"]["head_to_head"]
    assert h["H1_detection_at_b_star"]["mean_diff"] == pytest.approx(0.5)     # 1.0 − 0.5 per seed
    assert h["H2_floor"]["mean_diff"] == pytest.approx(1.0)                   # 2 − 1 per month
    assert "p_holm" in h["H1_detection_at_b_star"] and "p_holm" in h["H2_floor"]
    assert h["descriptive_by_budget"]["1"]["reachable"] is False and h["descriptive_by_budget"]["10"]["reachable"]
