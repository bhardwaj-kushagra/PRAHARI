"""Protocol R2 (docs/research/protocol-r2.md §9): the M20b haze geometry, R9 one-factor reference, R10 evidence gate,
R11 Mei procedure, and fidelity of the fast two-knob edge replay against the registered edge stages."""
import copy
import hashlib

import numpy as np
import pytest

from prahari.core.config import load_config
from prahari.core.pipeline import Simulation
from prahari.core.rng import make_rngs
from prahari.eval.experiments import protocol_config
from prahari.eval.offline import edge_alarms, edge_stages
from prahari.research.edge2 import alarms_at, edge_records
from prahari.research.gate import evidence_share, gated
from prahari.research.mei import mei_alarms
from prahari.research.operating import SeedEval, _cands, _hits, evaluate_seed
from prahari.research.operating_r2 import evaluate_seed_r2
from prahari.research.record import factor_input, fit_factor_gain
from prahari.research.runner_r2 import load_r2, scenario_config
from prahari.sensors.haze import front_delays, gain_field, night_factor, swath_coverage

from ..conftest import REPO


def test_m20_form_is_unchanged():
    """The default form draws exactly as release 1.0 (reference hash of 40 days of g_i H(t), seed 11, golden)."""
    cfg = load_config(REPO / "configs" / "experiments" / "golden.yaml")
    cfg["run"]["seed"], cfg["run"]["days"] = 11, 40
    sim = Simulation(cfg)
    sim.prepare()
    st = sim.slots["haze"].chain[0]
    out = np.zeros((40 * 1440, sim.ctx.n_nodes))
    for t in range(40 * 1440):
        sim.ctx.t = t
        out[t] = st.step(t, sim.ctx).v
    assert hashlib.sha256(out.tobytes()).hexdigest()[:16] == "f0b5228a5b856aca"


def test_front_delays_first_node_zero_and_speed():
    xy = np.array([[0.0, 0.0], [120.0, 0.0], [60.0, 50.0]])
    d = front_delays(xy, 0.0, 2.0)                                  # front moving along +x at 2 m/s
    assert d.tolist() == [0.0, 1.0, 0.5]                             # 120 m / 2 m/s = 60 s = 1 min
    assert front_delays(xy, 0.0, np.inf).tolist() == [0.0, 0.0, 0.0]


def test_swath_coverage_edges():
    xy = np.array([[0.0, y] for y in (0.0, 100.0, 140.0, 150.0, 160.0, 300.0)])
    c = swath_coverage(xy, 0.5, 0.0, 0.0, 600.0, 20.0, 0.1)         # axis along x, width 300 m centred at y = 0
    assert c.tolist() == pytest.approx([1.0, 1.0, 1.0, 0.55, 0.1, 0.1])
    assert swath_coverage(xy, 1.0, 0.3, 50.0, 600.0, 20.0, 0.1).tolist() == [1.0] * 6


def test_night_factor_keeps_the_mean_rate():
    f = np.array([night_factor(t, 0.7, [1200, 480]) for t in range(1440)])
    assert f.mean() == pytest.approx(1.0)
    night = (np.arange(1440) >= 1200) | (np.arange(1440) < 480)
    assert (f[night] * 1).sum() / f.sum() == pytest.approx(0.7)


def test_gain_field_is_spatially_correlated():
    xy = np.array([[0.0, 0.0], [20.0, 0.0], [1000.0, 0.0]])
    G = np.array([gain_field(xy, 0.3, 200.0, 0.7, (-9, 9), np.random.default_rng(s)) for s in range(4000)])
    near, far = np.corrcoef(G[:, 0], G[:, 1])[0, 1], np.corrcoef(G[:, 0], G[:, 2])[0, 1]
    assert near == pytest.approx(0.49 * np.exp(-0.1), abs=0.04)      # ρ_s² e^(−d/L)
    assert abs(far) < 0.05 and G.mean() == pytest.approx(1.0, abs=0.01) and G.std() == pytest.approx(0.3, abs=0.01)


def test_m20b_scripted_episode_reaches_nodes_with_delay():
    r2 = load_r2()
    cfg = scenario_config(r2, "H-mix")
    cfg["run"]["seed"], cfg["run"]["days"] = 11, 2
    cfg["params"]["haze"]["base_rate_per_10d"] = 0.0
    cfg["params"]["haze"]["scripted"] = [{"t_min": 100, "duration_min": 300, "amplitude": 2.0}]
    sim = Simulation(cfg)
    sim.prepare()
    st = sim.slots["haze"].chain[0]
    v = np.array([st.step(t, sim.ctx).v for t in range(900)])
    first = (v > 0).argmax(axis=0)
    meta = st.snapshot()["episodes"][0]
    assert first.min() >= 101 and first.max() <= 101 + meta["delay_max_min"]    # front delay + jitter
    assert first.max() - first.min() >= 5                            # arrival is spread across nodes
    assert v[:100].sum() == 0 and v[-1].sum() == 0                   # nothing before the start or after the end


def test_factor_gain_recovered_and_input():
    rng = np.random.default_rng(5)
    g = np.array([0.6, 0.9, 1.0, 1.1, 1.4])
    m = rng.uniform(0.5, 2.5, 400)
    D = m[:, None] * g[None, :] + 0.02 * rng.normal(size=(400, 5))
    gh = fit_factor_gain(D)
    assert np.allclose(gh / np.median(gh), g, atol=0.02)
    assert fit_factor_gain(D[:100]).tolist() == [1.0] * 5            # fewer than 120 minutes: ĝ = 1
    x, b = np.array([3.0, 5.0, 4.0]), np.array([1.0, 1.0, 2.0])
    assert factor_input(x, b, np.ones(3)).tolist() == [1.0, 3.0, 2.0]  # x − median(x − b) = x − 2


def test_evidence_share_and_gate():
    P = np.ones((6, 4))
    P[1, 0] = P[2, 1] = P[4, 2] = 0.005
    e = evidence_share(P, 0.01, 2)                                   # window (t − 2, t]
    assert e.tolist() == [0.0, 0.25, 0.5, 0.25, 0.25, 0.25]
    al = [(1, 0, [0]), (2, 1, [1]), (5, 2, [2])]
    assert gated(al, e, 0.5) == [(1, 0, [0]), (5, 2, [2])]
    assert gated(al, e, None) == al


def test_mei_reference():
    P = np.ones((8, 3))
    P[2:5, 1] = np.exp(-4.0)                                         # S = 4 on node 1 for 3 ticks
    P[3, 0] = np.exp(-3.0)
    al = mei_alarms(P, [3.0, 100.0], k=1.5, refractory=2, t0=10)
    # t=2: W1 = 2.5; t=3: W1 = 5, W0 = 1.5, sum 6.5 > 3 → alarm at 13, anchor 1, members {W ≥ 2.5}; reset
    # t=4: W1 = 2.5 (refractory); t=5: W1 = 1.0 (ref 0 but sum 1 ≤ 3)
    assert al[0] == [(13, 1, [1])] and al[1] == []


def short_cfg():
    cfg = load_config(REPO / "configs" / "experiments" / "golden.yaml")
    ev = cfg["params"]["evaluation"]
    ev["calibration_days"], ev["tuning_days"], ev["test_days"] = 2, 2, 4
    cfg["world"]["n_nodes"] = 36
    return cfg


@pytest.fixture(scope="module")
def seed11():
    return SeedEval(short_cfg(), 11, ("main", "med", "factor"))


def test_fast_replay_equals_edge_stages_at_every_rho(seed11):
    se = seed11
    tq = se.q.nodes["main"]
    p = tq.params
    hq, _, _ = se.tuned_both(tq.s, tq.frac, tq.s, tq.frac, [3.0, 10.0], tq.k, p, (5000.0, 22))
    for hits in _hits(tq.s, se.test0, tq.k, hq, int(p["refractory_min"])):
        cands = _cands(hits, tq.p)
        recs = edge_records(cands, se.cfg, se.sim.ctx, make_rngs(se.seed)["srp"])
        assert recs
        for rho in [0, 1.5, 2, 3, 4, 6, 10]:
            c = copy.deepcopy(se.cfg)
            mods = {"scmr": "stub"} if rho == 0 else {}
            c["params"]["scmr"]["ratio_min"] = float(rho)
            ref = edge_alarms(cands, edge_stages(c, se.sim.ctx, make_rngs(se.seed)["srp"], mods), se.sim.ctx)
            assert alarms_at(recs, rho) == ref, rho


def test_r2_path_reproduces_r1_p2_on_the_release_haze():
    """H-sync continuity: with the release-1.0 haze, R2's P2 at ρ = 3 (the configured M31 threshold) equals R1's P2
    row, and R2's P2-med equals R1's P2-med, knob by knob (development seed 11, short protocol)."""
    grids = {"P0": [5], "P1": [48], "v1t": [1, 3], "node": [1, 3, 10]}
    r1 = evaluate_seed(short_cfg(), 11, grids, (5000.0, 22), ("P2", "P2-med"))
    g2 = {**load_r2()["grids"], "node": [1, 3, 10], "v1t": [1, 3]}
    r2 = evaluate_seed_r2(short_cfg(), 11, g2, (5000.0, 22))
    p2 = r2["pipelines"]["P2"]
    j = [i for i, (r, rho) in enumerate(p2["grid"]) if rho == 3.0]
    assert [p2["false_incidents"][i] for i in j] == r1["pipelines"]["P2"]["false_incidents"]
    assert [p2["latencies"][i] for i in j] == r1["pipelines"]["P2"]["latencies"]
    for key in ("false_incidents", "latencies"):
        assert r2["pipelines"]["P2-med"][key] == r1["pipelines"]["P2-med"][key]
        assert r2["pipelines"]["AR"][key] == r1["pipelines"]["AR"][key]
    assert r2["factor_gain"] is not None and len(r2["factor_gain"]) == 36
