"""Phase 4 tests: M44, M45 (SPEC §9.2), M46 counting rules, and the P0/P1 baselines cross-checked against the
report's reference simulation on identical inputs."""
import importlib.util
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from prahari.core.clock import Clock
from prahari.core.contracts import Readings
from prahari.core.context import RunContext
from prahari.detect.baselines.fixed import FixedThreshold
from prahari.detect.baselines.v1 import V1AsWritten
from prahari.eval.stats import detect, incidents, per_month, poisson_ci, wilson

ORACLE_PATH = Path(__file__).resolve().parents[3] / "reference" / "prahari_simulation.py"


@pytest.fixture(scope="module")
def oracle():
    spec = importlib.util.spec_from_file_location("prahari_oracle", ORACLE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# -- M44, M45 (§9.2) ------------------------------------------------------------------
def test_m44_wilson_reference_value():
    lo, hi = wilson(272, 328)
    assert 272 / 328 == pytest.approx(0.829, abs=5e-4)
    assert lo == pytest.approx(0.785, abs=5e-4) and hi == pytest.approx(0.866, abs=5e-4)


def test_m45_poisson_reference_value():
    r = per_month(32, 150)
    assert r["rate"] == pytest.approx(6.4)
    assert r["ci95"][0] == pytest.approx(4.4, abs=0.05) and r["ci95"][1] == pytest.approx(9.0, abs=0.05)
    assert poisson_ci(0)[0] == 0.0 and poisson_ci(0)[1] == pytest.approx(3.689, abs=1e-3)


def test_m45_reproduces_the_report_interval_for_p0():
    r = per_month(1457, 150)                     # 291.4 per month over 5 × 30 test days
    assert r["ci95"][0] == pytest.approx(277, abs=1) and r["ci95"][1] == pytest.approx(306.5, abs=1)


# -- M46 against the oracle ---------------------------------------------------------------
def random_alarms(rng, n=400, t_max=5000):
    ts = np.sort(rng.integers(0, t_max, n))
    return [(int(t), int(i), [int(i)] + ([int(i) + 1] if i < 99 and rng.random() < 0.3 else []))
            for t, i in zip(ts, rng.integers(0, 100, n))]


def test_m46_incidents_and_detect_match_the_oracle(oracle):
    xy, dist, R = oracle.geometry(70.0)
    rng = np.random.default_rng(1)                                        # test fixture only
    for _ in range(5):
        al = random_alarms(rng)
        assert incidents(al, dist, R, 500, 4500) == oracle.incidents(al, dist, R, 500, 4500)
        fires = [(int(t), rng.uniform(0, 630, 2)) for t in rng.integers(0, 4800, 12)]
        assert detect(al, fires, xy) == oracle.detect(al, fires, xy)


def test_m46_merging_rules_by_hand():
    xy = np.array([[0.0, 0.0], [70.0, 0.0], [500.0, 0.0]])
    dist = np.hypot(xy[:, None, 0] - xy[None, :, 0], xy[:, None, 1] - xy[None, :, 1])
    al = [(0, 0, [0]), (50, 1, [1]), (200, 1, [1]), (210, 2, [2])]
    # 0 and 1 merge (≤ 60 min, ≤ 2R = 224 m); 200 is too late; node 2 is too far
    assert incidents(al, dist, 112.0, 0, 1000) == 3
    assert detect(al, [(40, np.array([60.0, 0.0])), (300, np.array([0.0, 0.0]))], xy) == [10, None]


# -- M22 / M23 baselines against the oracle on identical inputs -------------------------------
def step_all(stage, xc, xr, start):
    xy = np.array([(a, b) for a in np.arange(10) * 70.0 for b in np.arange(10) * 70.0])
    ctx = RunContext(clock=Clock(datetime(2026, 4, 15), xc.shape[1] / 1440, 1), xy=xy, spacing_m=70.0, radius_m=112.0)
    stage.reset(ctx)
    cands, alarms = [], []
    for t in range(xc.shape[1]):
        ctx.t = t
        out = stage.step(Readings(x=xc[:, t][:, None], x_raw=xr[:, t][:, None]), ctx)
        out.validate(100)
        cands += [(t, i) for i in out.candidates]
        alarms += [(t, i, sorted(m)) for i, m in out.alarms]
    return cands, alarms


def synthetic(seed=3, T=4000):
    rng = np.random.default_rng(seed)                                    # test fixture only
    t = np.arange(T)
    x = 0.3 * np.sin(2 * np.pi * (t % 1440) / 1440)[None, :] + np.cumsum(rng.normal(0, 0.03, (100, T)), axis=1)
    x += rng.standard_t(3, (100, T)) * 0.1
    spikes = rng.random((100, T)) < 0.002
    return (x + 3.0 * spikes).astype(np.float32)


def test_m22_p0_matches_oracle(oracle, smoke_cfg):
    xr = synthetic(4)
    start = 2000
    p = dict(smoke_cfg["params"]["baseline_p0"], start_min=start)
    _, ours = step_all(FixedThreshold(p, None), xr, xr, start)
    thr = xr[:, :1440].mean(1) + 3 * xr[:, :1440].std(1)
    ref = oracle.p0_alarms(xr, thr, start, xr.shape[1])
    assert len(ours) > 20
    assert [(t, i) for t, i, _ in ours] == [(t, i) for t, i, _ in ref]


def test_m23_p1_matches_oracle(oracle, smoke_cfg):
    xc = synthetic(5)
    start = 2000
    p = dict(smoke_cfg["params"]["baseline_p1"], start_min=start)
    cands, alarms = step_all(V1AsWritten(p, None), xc, xc, start)
    z1 = oracle.ewma_z(xc, lockup_fix=False)
    ref_c = oracle.cusum(z1, 0.5, 8.8, start, xc.shape[1])
    xy, dist, R = oracle.geometry(70.0)
    ref_a = oracle.confirm(ref_c, dist, R, np.ones(10, bool), False, False)
    assert len(cands) > 20 and cands == [(t, i) for t, i in ref_c]
    assert [(t, i, sorted(m)) for t, i, m in ref_a] == alarms
