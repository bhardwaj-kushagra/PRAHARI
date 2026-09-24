"""Phase 9: sensor faults (M21) and health weights (M29) — acceptance 3: a stuck sensor's health weight falls below
0.1 within 90 minutes."""
from datetime import datetime

import numpy as np
import pytest

from prahari.core.clock import Clock
from prahari.core.context import RunContext
from prahari.core.contracts import PValues, Readings, Residuals
from prahari.detect.prahari.score_real import ScoreReal, health_weight, robust_z
from prahari.sensors.faults_real import FaultsReal

XY = np.array([(a, b) for a in np.arange(10) * 70.0 for b in np.arange(10) * 70.0])


def ctx(days=4.0):
    return RunContext(clock=Clock(datetime(2026, 4, 15), days, 1), xy=XY, spacing_m=70.0, radius_m=112.0)


def quiet(T, seed=1):
    rng = np.random.default_rng(seed)                                        # test fixture only
    e = np.zeros((T, 100))
    for t in range(1, T):
        e[t] = 0.95 * e[t - 1] + rng.normal(0, 0.05, 100)
    return e + 0.3 * np.sin(2 * np.pi * np.arange(T) / 1440)[:, None]


def run_faults(params, x, c):
    st = FaultsReal(params, np.random.default_rng(7))
    st.reset(c)
    out = []
    for t in range(x.shape[0]):
        c.t = t
        r = st.step(Readings(x=x[t][:, None], x_raw=x[t][:, None] + 1.0), c)
        r.validate(100)
        out.append(r)
    return out


def test_scripted_faults_do_what_m21_says(smoke_cfg):
    p = dict(smoke_cfg["params"]["faults"], rate_per_node_30d={k: 0.0 for k in ("stuck", "offset", "spike", "dropout")},
             scripted=[{"node": 1, "kind": "stuck", "t_min": 100, "duration_min": 50},
                       {"node": 2, "kind": "offset", "t_min": 100, "value_su": 1.2},
                       {"node": 3, "kind": "spike", "t_min": 100, "duration_min": 8},
                       {"node": 4, "kind": "dropout", "t_min": 100, "duration_min": 30}])
    x = quiet(300)
    out = run_faults(p, x, ctx())
    X = np.array([r.x[:, 0] for r in out])
    assert (X[100:150, 1] == X[99, 1]).all() and X[150, 1] == pytest.approx(x[150, 1])      # stuck, then released
    assert np.allclose(X[100:, 2] - x[100:, 2], 1.2)                                         # permanent offset
    assert np.allclose(np.abs(X[100:108, 3] - x[100:108, 3]), 5.0) and np.allclose(X[108:, 3], x[108:, 3])
    miss = np.array([r.missing[4] for r in out])
    assert miss[100:130].all() and not miss[:100].any() and not miss[130:].any()
    assert (X[100:130, 4] == X[99, 4]).all()                                                 # held, never NaN
    assert out[120].fault[[1, 2, 4]].all() and not out[120].fault[0]


def test_fault_rates(smoke_cfg):
    p = dict(smoke_cfg["params"]["faults"], rate_per_node_30d={"stuck": 0.0, "offset": 0.0, "spike": 0.0, "dropout": 3.0})
    st = FaultsReal(p, np.random.default_rng(8))
    c = ctx(10)
    st.reset(c)
    n = 0
    for t in range(10 * 1440):
        c.t = t
        st.step(Readings(x=np.zeros((100, 1)), x_raw=np.zeros((100, 1))), c)
        n += len(st.started)
    assert n == pytest.approx(100 * 3.0 * 10 / 30, rel=0.15)                  # 100 per node-period, 10 of 30 days


def health_run(params, x, missing=None):
    c = ctx(x.shape[0] / 1440 + 0.01)
    st = ScoreReal(params, None)
    st.reset(c)
    H = []
    for t in range(x.shape[0]):
        c.t = t
        rd = Readings(x=x[t][:, None], x_raw=x[t][:, None], missing=None if missing is None else missing[t])
        res = Residuals(r=np.zeros((100, 1)), z=np.zeros((100, 1)), b=x[t][:, None])
        sc = st.step((PValues(p=np.full((100, 1), 0.5), n_cal=np.zeros(100)), rd, res), c)
        sc.validate(100)
        H.append(sc.c[:, 0])
    return np.array(H)


def test_acceptance_3_stuck_sensor_abstains_within_90_minutes(smoke_cfg):
    x = quiet(4000)
    ts = 3000
    x[ts:, 17] = x[ts - 1, 17]                                                # node 17 freezes at its last value
    H = health_run(smoke_cfg["params"]["score"], x)
    below = np.flatnonzero(H[ts:, 17] < 0.1)
    assert below.size and below[0] <= 90                                      # within 90 minutes
    assert (H[ts + 90:, 17] < 0.1).all() and np.median(H[ts:, 16]) == 1.0    # stays out; a neighbour keeps weight 1


def test_dropout_and_offset_lower_the_weight(smoke_cfg):
    x = quiet(3000)
    miss = np.zeros((3000, 100), dtype=bool)
    miss[2000:2100, 5] = True
    x[1500:, 44] += 30.0                                                      # a gross baseline offset
    H = health_run(smoke_cfg["params"]["score"], x, miss)
    assert H[2006:2100, 5].max() == 0.0 and H[1990, 5] > 0.9 and H[2110, 5] > 0.9   # abstains while not fresh
    assert H[2999, 44] < 0.1                                                  # neighbour consensus (q ≫ 3)
    assert health_weight(np.array([1.0]), np.array([1.0]), np.array([3.0]))[0] == 1.0
    assert robust_z(np.array([0.0, 0.0, 0.0])).tolist() == [0.0, 0.0, 0.0]
