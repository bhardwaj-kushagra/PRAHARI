"""Research track R1 statistics (protocol §3, R4–R8) against hand-computed reference values."""
import numpy as np
import pytest

from prahari.core.rng import make_rngs
from prahari.research import pstats as ps
from prahari.research.runner import load_r1, seed_list, sweep_points


def matrix(knob, grid, F, D, n, days=30.0):
    F, D = np.array(F, float), np.array(D, float)
    return {"F": F, "D": D, "n": np.array(n, float), "days": np.full(F.shape[0], days), "grid": grid, "knob": knob}


def test_select_most_permissive_within_budget():
    # target knob: larger is more permissive; pooled FA per month = F summed over 2 seeds × 30 d / 60 d
    m = matrix("target", [0.5, 1, 2, 4], [[0, 1, 2, 4], [1, 1, 4, 8]], [[1, 2, 3, 4]] * 2, [10, 10])
    assert ps.pooled(m)["fa"].tolist() == [0.5, 1.0, 3.0, 6.0]
    assert ps.select(m, 3) == 2 and ps.select(m, 0.4) is None
    # h knob: smaller is more permissive
    h = matrix("h", [1, 2, 3, 4], [[10, 5, 2, 1]], [[4, 3, 2, 1]], [10])
    assert ps.select(h, 3) == 2 and ps.select(h, 100) == 0


def test_holm_reference():
    out = ps.holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert [round(out[k]["p_holm"], 6) for k in "abc"] == [0.03, 0.06, 0.06]
    assert out["a"]["reject"] and not out["b"]["reject"]


def test_interpolation_and_pauc():
    assert ps.interp_det([1, 10], [0.2, 0.8], 10 ** 0.5) == pytest.approx(0.5)
    assert ps.interp_det([1, 10], [0.2, 0.8], 0.5) == 0.0                      # below the lowest FA: not reachable
    assert ps.interp_det([1, 10], [0.2, 0.8], 50) == pytest.approx(0.8)
    assert ps.pauc([0.1, 100], [0.6, 0.6], 0.5, 10) == pytest.approx(0.6)
    # reachable only from FA 1: zero over [0.5, 1) — a third of log10 range [0.5, 10] is log10(2)/log10(20)
    assert ps.pauc([1, 100], [0.6, 0.6], 0.5, 10) == pytest.approx(0.6 * (1 - np.log10(2) / np.log10(20)), abs=2e-3)


def test_bootstrap_weights_and_paired_comparison():
    W = ps.resample_weights(5, 200, make_rngs(1)["research"])
    assert W.shape == (200, 5) and np.all(W.sum(axis=1) == 5)
    a, b = np.array([0.8, 0.7, 0.9, 0.6, 0.75]), np.array([0.6, 0.6, 0.7, 0.5, 0.65])
    c = ps.paired(a, b, W)
    assert c["mean_diff"] == pytest.approx(0.14) and c["wins"] == 5 and c["losses"] == 0
    assert c["ci95"][0] > 0 and c["p_wilcoxon"] == pytest.approx(0.0625)      # 5 positive ranks: exact 2/32


def test_protocol_config_seeds_and_sweeps():
    r1 = load_r1()
    assert seed_list(r1["seeds"]["selection"]) == list(range(901, 921))
    assert seed_list(r1["seeds"]["test"]) == list(range(1001, 1101))
    labels = [lab for lab, _ in sweep_points(r1, {"params": {"nuisance": {"rate_roadside_per_day": 1.0,
                                                                          "rate_other_per_day": 0.2},
                                                             "sensor": {"drift_step_sd": 0.002, "ageing_sd": 0.5}}})]
    assert "ar_phi=0.8" in labels and "nuisance=x2" in labels and "plume=real" in labels and len(labels) == 20
