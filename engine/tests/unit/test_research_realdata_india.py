"""Addendum C (India real data): preprocessing rules, the front fit, the Wilson interval, the Princeton date and
header rules, and the observation operator's limiting cases (reference values)."""
import copy

import numpy as np
import pytest

from prahari.core.rng import make_rngs
from prahari.research.realdata_india import (carry_forward, front_fit, operator, parse_princeton, stuck_to_nan,
                                             wilson)
from prahari.research.runner_r2 import load_r2, scenario_config


def test_stuck_runs_of_six_hours_become_missing():
    g = np.array([1.0, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, np.nan, 4])
    out = stuck_to_nan(g, 3600)                                # ≥ 6 h at 1 h ticks: six identical values
    assert np.isnan(out[1:7]).all() and out[7:12].tolist() == [3, 3, 3, 3, 3] and out[13] == 4
    assert np.isfinite(stuck_to_nan(g, 900)[1:7]).all()        # 6 values at 15 min = 1.5 h: kept


def test_carry_forward_one_bin():
    g = np.array([1.0, np.nan, np.nan, 2.0, np.nan])
    assert np.allclose(carry_forward(g, 1), [1, 1, np.nan, 2, 2], equal_nan=True)
    assert np.allclose(carry_forward(g, 0), g, equal_nan=True)


def test_front_fit_recovers_a_plane():
    rng = np.random.default_rng(4)
    xy = rng.uniform(-20, 20, (12, 2))                        # km
    speed, direction = 3.0, np.radians(60.0)                    # m/s, travelling towards 060°
    s = np.array([np.sin(direction), np.cos(direction)]) / (speed * 60.0 / 1000.0)   # min per km
    t_min = 30 + xy @ s
    f = front_fit(t_min / 15.0, xy, 900)                       # ticks of 15 min
    assert f["speed_ms"] == pytest.approx(3.0, rel=1e-6) and f["direction_deg"] == pytest.approx(60.0, abs=1e-6)
    assert f["r2"] == pytest.approx(1.0) and f["residual_sd_min"] == pytest.approx(0.0, abs=1e-6)
    assert front_fit([0, 1, 2, 3], xy[:4], 900) is None        # fewer than 5 stations


def test_wilson_reference():
    assert wilson(7, 10) == [0.397, 0.892]
    assert wilson(0, 0) is None


def test_princeton_rules(tmp_path):
    good = tmp_path / "Delhi_X.csv"
    rows = ["From Date,To Date,PM10,PM2.5,State,City,Station,lat,lon"]
    rows += [f"{d}/1/2015 {h}:00,x,1,{10 + h},Delhi,Delhi,X,28.6,77.2" for d in (1, 2) for h in range(24)]
    rows += [",,,,,,,,"]                                        # blank trailing row
    good.write_text("\n".join(rows) + "\n", encoding="utf-8")
    rec = parse_princeton(good)
    assert "excluded" not in rec and rec["station"] == "X" and len(rec["epochs"]) == 48
    assert rec["epochs"][24] - rec["epochs"][0] == 86400       # 2/1/2015 is 2 January (day-first)
    assert rec["epochs"][0] == 1420050600                      # 1 Jan 2015 00:00 IST = 31 Dec 2014 18:30 UTC
    dup = tmp_path / "Delhi_Y.csv"
    dup.write_text("From Date,To Date,PM2.5,Ozone,PM2.5,State,City,Station,lat,lon\n", encoding="utf-8")
    assert parse_princeton(dup)["excluded"].startswith("PM2.5 column ambiguous")


def test_operator_limits():
    haze = copy.deepcopy(scenario_config(load_r2(), "H-mix")["params"]["haze"])
    haze.update(coverage_full_prob=1.0, front_speed_ms=None, jitter_max_range_min=[0.0, 0.0])
    ll = np.array([[28.5 + 0.05 * i, 77.0 + 0.04 * (i % 3)] for i in range(8)])
    op = operator(ll, haze, make_rngs(1)["research"], 3600, n=200)
    assert op["share_involved_q05_50_95"] == [1.0, 1.0, 1.0] and op["p_full_coverage"] == 1.0
    assert op["onset_spread_min_q05_50_95"] == [0.0, 0.0, 0.0]
    assert 0.1 < op["cv_q05_50_95"][1] < 0.9                    # σ_g = 0.3 and s_e ∈ [0.1, 0.6]
