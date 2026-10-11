"""Protocol R4 implementation checks (protocol-r4.md §9) on development seed 11 with a short configuration, and the
R4 analysis on synthetic seed files: the configuration reuses R2/R3 unchanged apart from the rate and the strict node
targets; haze-off and haze-on runs of one seed are paired (same fires, identical readings until the first haze
minute); adding strict targets leaves the other cells unchanged; selection with the useful floor; family P."""
import json
import re

import numpy as np
import pytest

from prahari.core.config import load_config
from prahari.research.analysis_r4 import method_differences, useful_floor_index, write_analysis_r4, write_test_table_r4
from prahari.research.archive import archive_seeds, extract_seeds
from prahari.research.numbers import rows_r4_selection
from prahari.research.operating import SeedEval
from prahari.research.operating_r2 import evaluate_seed_r2
from prahari.research.runner_r2 import load_r2, scenario_config

from ..conftest import REPO

R4 = "configs/research/r4.yaml"
METHODS = ("P2", "P2-medSCMR", "P2-gate")


def _short(cfg):
    ev = cfg["params"]["evaluation"]
    ev["calibration_days"], ev["tuning_days"], ev["test_days"] = 2, 2, 4
    cfg["world"]["n_nodes"] = 36
    return cfg


def test_r4_config_reuses_r2_r3_and_seeds_are_fresh():
    r2, r3, r4 = load_r2(), load_r2("configs/research/r3.yaml"), load_r2(R4)
    assert r4["m20b"] == r2["m20b"] and r4["cap"] == r2["cap"] and r4["methods"] == list(METHODS)
    for k in ("v1t", "rho", "theta", "gate_p", "gate_window_min"):
        assert r4["grids"][k] == r2["grids"][k]
    assert r4["grids"]["node"] == [0.03, 0.05] + r2["grids"]["node"]
    assert scenario_config(r4, "H-mix") == scenario_config(r3, "H-mix")       # H-mix is R2/R3's H-mix exactly
    rates = {sc: scenario_config(r4, sc)["params"]["haze"]["crop_burning_multiplier"] for sc in r4["scenarios"]}
    assert rates == {"H-none": 0.0, "H-mix": 1.0, "H-mix-x0.3": 0.3, "H-mix-x3": 3.0}
    assert r4["scenarios"]["H-none"]["seeds"] == r4["scenarios"]["H-mix"]["seeds"]   # paired by seed number
    used = set(range(11, 34))
    for st in load_r2("configs/research/r1.yaml")["seeds"].values():
        used |= set(range(st["from"], st["to"] + 1))
    for r in (r2, r3):
        for sc in r["scenarios"].values():
            for st in sc["seeds"].values():
                used |= set(range(st["from"], st["to"] + 1))
    for sc in r4["scenarios"].values():
        for st in sc["seeds"].values():
            assert not used & set(range(st["from"], st["to"] + 1))


def test_haze_off_and_on_are_paired_by_seed():
    """§9.1 — same fires and day types; readings identical in both passes until the first haze minute."""
    r4 = load_r2(R4)
    off = SeedEval(_short(scenario_config(r4, "H-none")), 11, ("main",))
    on = SeedEval(_short(scenario_config(r4, "H-mix-x3")), 11, ("main",))   # ×3, so the short run has haze
    assert len(off.fires) == len(on.fires) and np.array_equal(off.dry, on.dry)
    for (ta, pa), (tb, pb) in zip(off.fires, on.fires):
        assert ta == tb and np.array_equal(np.asarray(pa), np.asarray(pb))
    assert not off.q.haze.any() and on.q.haze.any()
    first = int(np.argmax(on.q.haze > 0))
    assert first > 0
    for a, b in ((off.q, on.q), (off.f, on.f)):
        assert np.array_equal(a.x[:first], b.x[:first])
    free = on.q.haze == 0
    share = float(np.mean(np.all(off.q.x[free] == on.q.x[free], axis=1)))
    print(f"pairing: first haze minute {first}; share of haze-free minutes with identical readings {share:.4f}")


def test_strict_targets_leave_other_cells_unchanged():
    """§9.2–9.3 — adding r = 0.03 to the node grid changes no other cell; the strict tuning runs and records caps."""
    r4 = load_r2(R4)
    cfg = _short(scenario_config(r4, "H-mix"))
    g = {**r4["grids"], "node": [0.1, 1], "rho": [0, 10], "theta": [0.05, None]}
    base = evaluate_seed_r2(cfg, 11, g, (5000.0, 22), METHODS)
    wide = evaluate_seed_r2(cfg, 11, {**g, "node": [0.03, 0.1, 1]}, (5000.0, 22), METHODS)
    for m in METHODS:
        b, w = base["pipelines"][m], wide["pipelines"][m]
        keep = [i for i, c in enumerate(w["grid"]) if c[0] != 0.03]
        for key in ("false_incidents", "latencies", "fi_starts", "fi_longest_min", "n_alarms_quiet"):
            assert [w[key][i] for i in keep] == b[key], (m, key)
        assert [w["grid"][i] for i in keep] == b["grid"]
        assert len(w["at_cap_by_target"]) == 3 and np.isfinite(w["h_by_target"][0]) and w["h_by_target"][0] > 0
        print(m, "r = 0.03: h", w["h_by_target"][0], "at cap", w["at_cap_by_target"][0])


def test_useful_floor_reference_values():
    fa, det = [0.0, 1.0, 6.0, 1.0], [0.0, 0.5, 1.0, 0.6]
    assert useful_floor_index(fa, det, None, 0.5) == 3                    # lowest FA among det ≥ 0.5, tie → higher det
    assert useful_floor_index(fa, det, [True, True, True, False], 0.5) == 1
    assert useful_floor_index(fa, det, None, 1.1) is None


def _row(seed, fi, lat, episodes):
    def pipe():
        return {"knob": "target×rho", "grid": [[0.03, 10.0], [0.1, 10.0], [1.0, 10.0]], "false_incidents": fi,
                "latencies": lat, "fi_starts": [[40400 + 10 * k for k in range(n)] for n in fi],
                "fi_longest_min": [60, 60, 60], "n_alarms_quiet": [1, 2, 9], "h_by_target": [900.0, 300.0, 100.0],
                "at_cap_by_target": [True, False, False]}
    return {"seed": seed, "test_days": 30, "n_fires": 2, "degraded": [], "haze_episodes": episodes,
            "fires_haze_overlap": [False, False], "pipelines": {m: pipe() for m in METHODS}}


def test_r4_analysis_on_synthetic_seeds(tmp_path):
    r4 = {**load_r2(R4), "bootstrap": {"seed": 1, "resamples": 200}}
    seeds = {"selection": {"from": 5901, "to": 5904}, "test": {"from": 6001, "to": 6008}}
    r4["scenarios"] = {sc: {**r4["scenarios"][sc], "seeds": seeds} for sc in ("H-none", "H-mix")}
    none = ([0, 0, 2], [[None, None], [30, 40], [20, 30]], [])                 # no haze: cell 1 detects both at 0 FA
    mix = ([0, 1, 6], [[None, None], [30, None], [20, 30]], [[40390, 40450, 1.0]])
    for stage, rng_ in (("selection", range(5901, 5905)), ("test", range(6001, 6009))):
        for sc, (fi, lat, ep) in (("H-none", none), ("H-mix", mix)):
            d = tmp_path / "r4" / stage / sc
            d.mkdir(parents=True)
            for s in rng_:
                (d / f"seed{s}.json").write_text(json.dumps(_row(s, fi, lat, ep)))
    write_analysis_r4(r4, tmp_path, selection_only=True)
    sel = json.loads((tmp_path / "r4_selection.json").read_text())["selection"]
    assert sel["H-none"]["methods"]["P2"]["operating"]["1"]["cell"] == [0.1, 10.0]
    assert sel["H-mix"]["methods"]["P2"]["operating"]["1"]["cell"] == [0.1, 10.0]
    assert sel["H-mix"]["methods"]["P2"]["operating"]["0.3"]["cell"] == [0.03, 10.0]
    assert sel["H-mix"]["methods"]["P2"]["floor"]["cell"] == [0.03, 10.0]
    assert sel["H-mix"]["methods"]["P2"]["useful_floor"]["cell"] == [0.1, 10.0]
    assert sel["H-mix"]["methods"]["P2"]["floor_r_ge_0.1"]["cell"] == [0.1, 10.0]
    assert sel["H-none"]["methods"]["P2"]["floor"]["cell"] == [0.1, 10.0]        # tie at 0 FA → higher detection
    assert not (tmp_path / "r4_analysis.json").exists()
    sfile = json.loads((tmp_path / "r4_selection.json").read_text())
    for _, _, _, key in rows_r4_selection(sfile):                              # every number-table key resolves
        node = sfile
        for br, dot in re.findall(r"\[([^\]]+)\]|([^.\[\]]+)", key):
            node = node[br or dot]
    write_test_table_r4(r4, tmp_path)
    t = json.loads((tmp_path / "r4_test.json").read_text())
    assert t["scenarios"]["H-mix"]["pipelines"]["P2"]["false_incidents"][0] == [0, 1, 6]
    assert not (tmp_path / "r4_analysis.json").exists()                     # the table computes no endpoint
    write_analysis_r4(r4, tmp_path)
    a = json.loads((tmp_path / "r4_analysis.json").read_text())
    for m in METHODS:
        p = a["family_P"][m]
        assert p["mean_diff"] == pytest.approx(0.5) and p["seeds"] == 8 and "p_holm" in p   # 1.0 − 0.5 per seed
    assert a["descriptive"]["price_by_budget"]["0.3"]["P2"]["mean_diff"] == pytest.approx(1.0)
    fl = a["scenarios"]["H-mix"]["floors"]["P2"]
    assert fl["useful_floor"]["false_incidents"]["rate"] == pytest.approx(1.0)
    assert fl["share_capped_by_target"]["0.03"] == pytest.approx(1.0)
    assert a["scenarios"]["H-mix"]["methods"]["P2"]["at_b_star"]["det"] == pytest.approx(0.5)
    assert a["descriptive"]["dose_response"]["H-none"]["methods"]["P2"]["det_at_1"] == pytest.approx(1.0)
    assert a["descriptive"]["price_at_equal_fa"]["P2"]["1"] == pytest.approx(0.5)
    # §6.2 — every floor carries its haze split: H-mix's useful floor (cell 1) has one incident a month, inside the
    # episode; H-none's floor setting has none
    uf = a["scenarios"]["H-mix"]["floors"]["P2"]["useful_floor"]["decomposition"]
    assert uf["inside"] == pytest.approx(1.0) and uf["outside"] == 0 and uf["share_inside"] == pytest.approx(1.0)
    assert a["scenarios"]["H-none"]["floors"]["P2"]["floor"]["decomposition"]["count"] == 0
    # §6.4 — deployment-view floors in the dose table (H-none's own selection: floor cell 1, 0 FA, both fires)
    dn = a["descriptive"]["dose_response"]["H-none"]["methods"]["P2"]
    assert dn["floor_at_selected"] == {"cell": [0.1, 10.0], "fa_per_month": 0.0, "det": 1.0}
    assert a["descriptive"]["dose_response"]["H-mix"]["methods"]["P2"]["useful_floor_at_selected"]["fa_per_month"] == 1.0
    # §6.5 — method differences: identical synthetic methods give zero differences at every budget
    md = a["scenarios"]["H-mix"]["method_differences"]["1"]
    assert list(md) == ["P2-medSCMR − P2-gate", "P2 − P2-medSCMR", "P2 − P2-gate"]
    assert all(v["mean_diff"] == 0 and v["p_wilcoxon"] == 1.0 for v in md.values())
    # the committed test table is not rewritten differently by the full analysis
    assert json.loads((tmp_path / "r4_test.json").read_text()) == t


def test_method_differences_reference_values():
    """§6.5 on hand-made rows: P2-medSCMR detects both fires on every seed at its 1-a-month cell, P2-gate one on two
    seeds and none on two; P2 equals P2-gate."""
    def pipe(lat):
        return {"knob": "target×rho", "grid": [[0.1, 10.0]], "false_incidents": [0], "latencies": [lat]}
    gate = [[10, None], [10, None], [None, None], [None, None]]
    rows = [{"seed": i, "test_days": 30, "pipelines": {"P2-medSCMR": pipe([5, 6]), "P2-gate": pipe(g), "P2": pipe(g)}}
            for i, g in enumerate(gate)]
    op = {"operating": {"1": {"index": 0, "cell": [0.1, 10.0]}, "3": None}}
    sel = {"methods": {m: op for m in METHODS}}
    W = np.ones((50, 4))
    md = method_differences(rows, sel, {"budgets": [1, 3]}, W)
    d = md["1"]["P2-medSCMR − P2-gate"]
    assert d["mean_diff"] == pytest.approx(0.75) and d["wins"] == 4 and d["losses"] == 0   # (0.5 + 0.5 + 1 + 1) / 4
    assert md["1"]["P2 − P2-gate"]["mean_diff"] == 0 and md["1"]["P2 − P2-medSCMR"]["mean_diff"] == pytest.approx(-0.75)
    assert md["3"]["P2-medSCMR − P2-gate"] == {"reachable": False}


def test_seed_archive_is_byte_reproducible(tmp_path):
    for sc in ("A", "B"):
        d = tmp_path / "r9" / "test" / sc
        d.mkdir(parents=True)
        for s in (2, 1):
            (d / f"seed{s}.json").write_text(json.dumps({"seed": s, "sc": sc}))
    first = archive_seeds(tmp_path, "r9", "test").read_bytes()
    assert archive_seeds(tmp_path, "r9", "test").read_bytes() == first
    names = extract_seeds(tmp_path / "r9_seeds_test.tar.gz", tmp_path / "x")
    assert names == ["r9/test/A/seed1.json", "r9/test/A/seed2.json", "r9/test/B/seed1.json", "r9/test/B/seed2.json"]
    assert (tmp_path / "x" / "r9/test/B/seed2.json").read_text() == json.dumps({"seed": 2, "sc": "B"})


def test_golden_base_is_unchanged_by_r4():
    assert load_r2(R4)["base"] == "configs/experiments/golden.yaml"
    load_config(REPO / load_r2(R4)["base"])                                     # loads as before
