"""Phase 9: the satellite baseline (M37) on scripted fires — overpass choice, area threshold, misses and delays."""
from datetime import datetime

import numpy as np
import pytest

from prahari.core.clock import Clock
from prahari.core.context import RunContext
from prahari.core.contracts import Fire, Fires
from prahari.satellite.race import SatelliteReal, pass_minutes, plan_fire


def sat(params, days=3.0):
    ctx = RunContext(clock=Clock(datetime(2026, 4, 15), days, 1), xy=np.zeros((1, 2)), spacing_m=70.0, radius_m=112.0)
    st = SatelliteReal(params, np.random.default_rng(1))
    st.reset(ctx)
    return st, ctx


def test_pass_schedule_uses_local_times(smoke_cfg):
    sch = pass_minutes(0, 0, 1, smoke_cfg["params"]["satellite"]["passes"])
    assert [(t, p) for t, p, _ in sch] == [(90, "Aqua"), (90, "VIIRS"), (630, "Terra"), (810, "Aqua"), (810, "VIIRS"),
                                           (1350, "Terra")]


def test_afternoon_fire_is_seen_at_the_night_terra_pass(smoke_cfg):
    p = dict(smoke_cfg["params"]["satellite"], p_miss=0.0)
    st, ctx = sat(p)
    ctx.t = 840                                                              # day 1, 14:00
    out = st.step(Fires(active=(Fire(id=0, x=0, y=0, t0=840),), new=(0,)), ctx)
    plan = out.plan[0]
    assert plan["overpass_t"] == 1350 and plan["platform"] == "Terra"      # 13:30 already gone; area 500 m² at 15:15
    assert 1350 + 40 <= plan["alert_t"] <= 1350 + 60 and out.alert_t == ((0, plan["alert_t"]),)


def test_small_fire_waits_for_the_area_threshold(smoke_cfg):
    rng = np.random.default_rng(2)
    p = smoke_cfg["params"]["satellite"]
    sch = pass_minutes(0, 0, 3, p["passes"])
    pl = plan_fire(1320, sch, 20.0, 500.0, 0.0, p["delay_min"], rng)       # 22:00: only 30 min old at 22:30
    assert pl["overpass_t"] == 1440 + 90 and pl["sensor"] == "MODIS"       # 01:30 next day (Aqua before VIIRS)
    assert float(20.0 * (30 / 15) ** 2) < 500.0


def test_missed_passes_are_skipped_and_recorded(smoke_cfg):
    p = smoke_cfg["params"]["satellite"]
    sch = pass_minutes(0, 0, 3, p["passes"])
    always = plan_fire(840, sch, 20.0, 500.0, 1.0, p["delay_min"], np.random.default_rng(3))
    assert always["alert_t"] is None and len(always["passes"]) > 3 and not any(q["seen"] for q in always["passes"])


def test_miss_rate_matches_p_miss(smoke_cfg):
    p = smoke_cfg["params"]["satellite"]
    sch = pass_minutes(0, 0, 4, p["passes"])
    rng = np.random.default_rng(4)
    first = [plan_fire(840, sch, 20.0, 500.0, 0.2, p["delay_min"], rng)["overpass_t"] == 1350 for _ in range(4000)]
    assert np.mean(first) == pytest.approx(0.8, abs=0.02)
