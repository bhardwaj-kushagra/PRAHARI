"""Phase 3a tests: plume acceptance values (M12, M13, M16 via the growth and plume stages), M8 and Poisson ignition."""
from datetime import datetime

import numpy as np
import pytest
from scipy.stats import chi2

from prahari.core.clock import Clock
from prahari.core.contracts import Fire, Fires, FuelState, Weather
from prahari.core.context import RunContext
from prahari.fire.growth import GrowthStub
from prahari.fire.ignition import IgnitionReal, activity, sustained_probability
from prahari.fire.plume import PlumeStub
from prahari.record.frames import decode_plume_grid, plume_grid
from prahari.world.interfaces import inside_polygon
from prahari.world.landscape import LandscapeReal

WIND = Weather(T=30, RH=30, wind_ms=1.5, wind_dir_deg=270.0)          # from the west: smoke travels +x


def stages(cfg, sigma=0.0):
    """Growth and plume stages with Q_max = Q_ref (σ = 0) and, by default, intermittency off."""
    g = GrowthStub(dict(cfg["params"]["growth"], qmax_lognormal_sigma=0.0), np.random.default_rng(0))
    pl = PlumeStub(dict(cfg["params"]["plume"], intermittency_sigma=sigma), np.random.default_rng(0))
    return g, pl


def conc_at(cfg, node_xy, age, wind=WIND):
    g, pl = stages(cfg)
    ctx = RunContext(clock=Clock(datetime(2026, 4, 15), 1, 1), xy=np.asarray(node_xy, dtype=float),
                     spacing_m=70.0, radius_m=112.0)
    g.reset(ctx)
    fires = Fires(active=(Fire(id=0, x=500.0, y=500.0, t0=0),))
    src = g.step((age, fires, wind), ctx)
    return pl.step((src, wind), ctx).c, pl, src


def test_acceptance_1_and_2_downwind_and_upwind_at_50m(smoke_cfg):
    c, pl, src = conc_at(smoke_cfg, [[550.0, 500.0], [450.0, 500.0], [500.0, 550.0]], age=100_000)
    assert c[0] == pytest.approx(2.5, abs=0.1)            # 50 m straight downwind, full growth
    assert c[1] == pytest.approx(0.25, abs=0.02)          # 50 m straight upwind
    assert c[2] == pytest.approx(2.5 * (0.1 + 0.9 * 0.25), rel=1e-5)   # crosswind: M13 h(π/2) = 0.325
    grid = plume_grid(lambda pts: pl.field(pts, src, WIND), src.x, src.y, 1400, 1400, 10.0, 300.0)
    field = decode_plume_grid(grid)
    iy, ix = int((500 - grid["y0"]) // 10), int((550 - grid["x0"]) // 10)   # cell centred at (555, 505)
    assert field[iy, ix] == pytest.approx(2.5 * np.exp(-np.hypot(55, 5) / 40 + 50 / 40)
                                          * (0.1 + 0.9 * ((1 + 55 / np.hypot(55, 5)) / 2) ** 2), rel=2e-3)


@pytest.mark.parametrize("d,u", [(50.0, 1.5), (120.0, 1.0), (200.0, 3.0)])
def test_acceptance_3_arrival_delay_is_distance_over_wind_speed(smoke_cfg, d, u):
    wind = Weather(T=30, RH=30, wind_ms=u, wind_dir_deg=270.0)
    arrival = d / (u * 60.0)                                             # M16 — minutes
    ages = np.arange(0, int(np.ceil(arrival)) + 3)
    c = np.array([conc_at(smoke_cfg, [[500.0 + d, 500.0]], age=a, wind=wind)[0][0] for a in ages])
    assert (c[ages <= arrival] == 0).all() and (c[ages > arrival] > 0).all()
    assert int(np.flatnonzero(c > 0)[0]) == int(np.floor(arrival)) + 1


def test_m8_reference_values():
    # §9.2 — FFMC 84, a = −21, b = 0.25 → 0.5; SPEC §5.3 shape: ≈0.2 at 78, ≈0.9 at 92
    np.testing.assert_allclose(sustained_probability([84.0, 78.0, 92.0], -21.0, 0.25), [0.5, 0.182, 0.881], atol=1e-3)


def test_m3_activity_profile():
    a = activity(np.array([2.0, 7.5, 12.0, 19.5, 23.0]), 0.2, 1.0, (6.0, 9.0), (18.0, 21.0))
    np.testing.assert_allclose(a[[0, 2, 4]], [0.2, 1.0, 0.2])
    assert 0.2 < a[1] < 1.0 and 0.2 < a[3] < 1.0


def run_ignition(cfg, days, ffmc, expected, seed=7):
    world = cfg["world"]
    land = LandscapeReal(cfg["params"]["landscape"], None).step(world, None)
    p = dict(cfg["params"]["ignition"], expected_fires=expected, scripted=[{"t_min": 60, "x": 700, "y": 700}],
             fire_lifetime_min=10 ** 9)
    ctx = RunContext(clock=Clock(datetime(2026, 4, 15), days, 1), xy=np.zeros((1, 2)), spacing_m=70.0,
                     radius_m=112.0, landscape=land)
    st = IgnitionReal(p, np.random.default_rng(seed))
    st.reset(ctx)
    new = []
    for t in range(int(days * 1440)):
        ctx.t = t
        out = st.step((t, WIND, FuelState(ffmc=ffmc)), ctx)
        out.validate(1)
        new += [(t, f, c) for f, c in zip(out.new, out.new_causes)]
    return st, out, land, new


def test_poisson_ignitions_match_expected_count_and_cluster_near_interfaces(smoke_cfg):
    days, expected = 30, 60.0
    st, out, land, new = run_ignition(smoke_cfg, days, ffmc=90.0, expected=expected)
    poisson = [f for f in out.active if f.id != 0]
    k = len(poisson)
    lo, hi = 0.5 * chi2.ppf(0.025, 2 * k), 0.5 * chi2.ppf(0.975, 2 * k + 2)
    assert lo <= expected <= hi, k                                        # E[fires] matches the scenario value
    assert any(c == "scripted" for _, _, c in new) and sum(c == "poisson" for _, _, c in new) == k
    village = next(f for f in smoke_cfg["world"]["interfaces"] if f["kind"] == "village")["points"]
    xy = np.array([[f.x, f.y] for f in poisson])
    assert not inside_polygon(xy[:, 0], xy[:, 1], village).any()
    S = land.lam * land.forest
    at_fires = S[(xy[:, 1] // 10).astype(int), (xy[:, 0] // 10).astype(int)].mean()
    assert at_fires > 1.5 * S[land.forest].mean()                          # fires cluster near interfaces
    assert out.attempts >= k                                              # every fire was an attempt first


def test_poisson_ignitions_follow_the_activity_profile(smoke_cfg):
    p = smoke_cfg["params"]["ignition"]
    grid_h = np.arange(0, 24, 1 / 60)
    a = activity(grid_h, p["activity_night"], p["activity_day"], p["activity_ramp_up_h"], p["activity_ramp_down_h"])
    expect_day = a[(grid_h >= 9) & (grid_h < 18)].sum() / a.sum()            # ≈ 0.63 with the defaults
    _, _, _, new = run_ignition(smoke_cfg, 30, ffmc=90.0, expected=400.0, seed=11)
    hours = np.array([(t % 1440) / 60 for t, _, c in new if c == "poisson"])
    frac, n = ((hours >= 9) & (hours < 18)).mean(), len(hours)
    assert abs(frac - expect_day) < 3 * np.sqrt(expect_day * (1 - expect_day) / n)


def test_wet_fuel_suppresses_sustained_fires(smoke_cfg):
    _, dry, *_ = run_ignition(smoke_cfg, 10, ffmc=92.0, expected=20.0, seed=3)
    _, wet, *_ = run_ignition(smoke_cfg, 10, ffmc=70.0, expected=20.0, seed=3)
    assert len(wet.active) < len(dry.active) and wet.attempts > 0          # M8: attempts happen, few sustain


def test_zero_expected_fires_is_scripted_only(smoke_cfg):
    st, out, _, new = run_ignition(smoke_cfg, 0.2, ffmc=95.0, expected=0.0)
    assert [c for _, _, c in new] == ["scripted"] and out.attempts == 0


def test_fires_day_recording_has_plumes_and_conc(smoke_cfg, tmp_path):
    from prahari.core.config import load_config
    from ..conftest import SMOKE
    from ..helpers import run_cfg as run
    cfg = load_config(SMOKE.parent / "fires_day.yaml")
    _, health, rec = run(cfg, tmp_path / "f.prs.jsonl.gz")
    assert health["ignition"]["state"] == "real"
    causes = {e["cause"] for f in rec.frames for e in f["events"] if e["type"] == "ignition"}
    assert causes == {"scripted", "poisson"}
    plumes = [f for f in rec.frames if "plume" in f]
    assert plumes and all(f["fires"] for f in plumes)
    assert not any("plume" in f for f in rec.frames if not f["fires"])
    assert max(max(f["nodes"]["conc"]) for f in plumes) > 0.5
