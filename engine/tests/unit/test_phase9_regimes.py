"""Phase 9: Regime Cards (SPEC §8.1), the lightning term of M3 with SCMR's lightning relaxation (M31), and the M33
integral prior used per cluster by RAQ."""
import copy

import numpy as np
import pytest

from prahari.core.config import load_config
from prahari.core.contracts import Clusters, Prior
from prahari.core.pipeline import Simulation
from prahari.detect.prahari.decide_real import cluster_prior, integral_setup
from prahari.detect.prahari.edge_real import ScmrReal
from prahari.fire.ignition import activity, sustained_probability

from ..conftest import REPO


@pytest.mark.parametrize("name,channels,lightning", [("india", 3, False), ("canada", 8, True), ("usa", 8, False),
                                                     ("australia", 8, True)])
def test_regime_cards_compose(tmp_path, name, channels, lightning):
    scen = REPO / "configs" / "scenarios" / f"_regime_{name}.yaml"
    scen.write_text(f"regime: {name}\nscenario: {{name: t, description: t}}\n")
    try:
        cfg = load_config(scen)
    finally:
        scen.unlink()
    assert cfg["regime_card"]["name"] == name and cfg["params"]["comms"]["channels"] == channels
    assert cfg["regime_card"]["lightning"] is lightning


def storm_sim(smoke_cfg, storms):
    cfg = copy.deepcopy(smoke_cfg)
    cfg["run"]["days"] = 0.3
    cfg["params"]["ignition"]["storms"] = storms
    cfg["params"]["ignition"]["strike_ignition_prob"] = 1.0
    sim = Simulation(cfg)
    sim.prepare()
    return sim


def test_lightning_strikes_start_fires_and_flag_the_storm(smoke_cfg):
    sim = storm_sim(smoke_cfg, [{"t_min": 60, "duration_min": 60, "x": 700, "y": 700, "radius_m": 200,
                                 "strikes_per_min": 0.5}])
    flags, causes = [], []
    for tick, t in enumerate(sim.clock.minutes()):
        sim.ctx.tick = tick
        _, _, fires, *_ = sim.step_signals(t)
        flags.append(sim.ctx.storm)
        causes += list(fires.new_causes)
    assert causes.count("lightning") >= 5 and not any(flags[:60]) and all(flags[60:120])
    assert all(flags[120:300]) and not any(flags[300:])                     # held 180 min after the storm


def test_no_storm_no_draws(smoke_cfg):
    a, b = storm_sim(smoke_cfg, []), storm_sim(smoke_cfg, [])
    for tick, t in enumerate(a.clock.minutes()):
        a.ctx.tick = b.ctx.tick = tick
        xa, xb = a.step_signals(t)[-1], b.step_signals(t)[-1]
    assert np.array_equal(xa.x, xb.x) and not a.ctx.storm


def test_scmr_relaxes_under_the_lightning_flag(smoke_cfg):
    sim = storm_sim(smoke_cfg, [])
    st = ScmrReal(smoke_cfg["params"]["scmr"], None)
    cl = Clusters(members=((0, 1),), p=((1e-3, 1e-3),), anchor=(0,), n_recent=(10,))   # ratio (2/4)/(10/100) = 5? see below
    nb = int(sim.ctx.neighbours[0].sum())
    ratio = (2 / nb) / (10 / 100)
    sim.ctx.prior = Prior(odds=1e-4)
    calm = st.step(cl, sim.ctx)
    sim.ctx.prior = Prior(odds=1e-4, lightning=True)
    storm = st.step(cl, sim.ctx)
    assert calm.ratio[0] == pytest.approx(ratio)
    assert calm.passed[0] == (ratio >= 3.0) and storm.passed[0] == (ratio >= 1.5)


def test_m33_integral_prior_scale_and_monotonicity(smoke_cfg):
    sim = storm_sim(smoke_cfg, [])
    p = dict(smoke_cfg["params"]["srp"], form="integral")
    rate, disk = integral_setup(sim.ctx, p)
    a_day = sum(float(activity(m / 60, p["activity_night"], p["activity_day"], p["activity_ramp_up_h"],
                               p["activity_ramp_down_h"])) for m in range(1440))
    ps = float(sustained_probability(p["ps_reference_ffmc"], p["ps_a"], p["ps_b"]))
    assert rate.sum() * a_day * 30 * ps == pytest.approx(p["fires_per_30d"])      # the map expects fires_per_30d
    pr = Prior(odds=1e-4, lam=1.0 * 30, p_s=ps, lam_map=rate, disk=disk)
    o1, _ = cluster_prior((44,), pr)
    o2, _ = cluster_prior((44, 45), pr)
    o3, _ = cluster_prior((44, 45, 54), pr)
    assert 0 < o1 < o2 < o3 < 1e-2                                                 # a larger area, a larger prior
