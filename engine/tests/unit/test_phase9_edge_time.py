"""Phase 9: the edge windows candidates by the minute they were detected, not the minute their frame arrived
(approved fix for the Phase 8 finding, DECISIONS P8-11 / P9-1)."""
from datetime import datetime

import numpy as np

from prahari.core.clock import Clock
from prahari.core.context import RunContext
from prahari.core.contracts import Delivered
from prahari.detect.prahari.edge_real import ClusterReal

XY = np.array([[0.0, 0.0], [70.0, 0.0], [700.0, 700.0]])


def run(params, deliveries):
    ctx = RunContext(clock=Clock(datetime(2026, 4, 15), 1, 1), xy=XY, spacing_m=70.0, radius_m=112.0)
    st = ClusterReal(params, None)
    st.reset(ctx)
    out = {}
    for t, d in deliveries:
        ctx.t = t
        out[t] = st.step(d, ctx)
    return out


def test_delayed_frame_does_not_join_a_window_it_was_never_in(smoke_cfg):
    p = smoke_cfg["params"]["cluster"]
    # node 0 detected at minute 7, frame held until 30 (outage); node 1 detected and delivered at 48
    got = run(p, [(30, Delivered(nodes=(0,), p=(1e-3,), t_detect=(7,))), (48, Delivered(nodes=(1,), p=(1e-3,)))])
    assert got[48].members == ((1,),)                       # 48 − 7 > 30 min: separate
    got = run(p, [(30, Delivered(nodes=(0,), p=(1e-3,), t_detect=(20,))), (48, Delivered(nodes=(1,), p=(1e-3,)))])
    assert got[48].members == ((0, 1),)                     # 48 − 20 ≤ 30 min: together


def test_late_frame_joins_neighbours_detected_near_it(smoke_cfg):
    p = smoke_cfg["params"]["cluster"]
    got = run(p, [(10, Delivered(nodes=(1,), p=(1e-3,))), (50, Delivered(nodes=(0,), p=(1e-3,), t_detect=(15,)))])
    assert got[50].members == ((0, 1),)                     # detected 5 min apart, delivered 40 min apart


def test_in_order_candidates_behave_as_before(smoke_cfg):
    p = smoke_cfg["params"]["cluster"]
    a = run(p, [(5, Delivered(nodes=(0,), p=(1e-3,))), (30, Delivered(nodes=(1,), p=(1e-3,))),
                (40, Delivered(nodes=(1,), p=(1e-3,)))])
    assert a[30].members == ((0, 1),) and a[40].members == ((1,),)   # minute 5 is outside 40 − 30
