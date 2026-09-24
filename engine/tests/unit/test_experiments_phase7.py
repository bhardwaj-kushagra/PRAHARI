"""Phase 7 tests: the legacy per-fire wind, offline edge replay equal to the live edge, the operating dial's default
point equal to the live tuning, ablation grouping, and the combined report table."""
import copy
import json

import numpy as np

from prahari.core.config import load_config
from prahari.core.contracts import Fire, Fires, Weather
from prahari.eval.experiments import _groups, protocol_config, run_experiment
from prahari.eval.offline import ScoreRecorder, edge_alarms, edge_stages, replay_candidates, tuned_h
from prahari.eval.report import table
from prahari.fire.growth import GrowthStub
from prahari.fire.plume import PlumeStub

from ..conftest import REPO

SHORT = {"params": {"evaluation": {"calibration_days": 1, "tuning_days": 1, "test_days": 2}}}


def test_per_fire_wind_is_constant_per_fire_and_opt_in(smoke_cfg):
    from prahari.core.context import RunContext
    from prahari.core.clock import Clock
    from datetime import datetime
    ctx = RunContext(clock=Clock(datetime(2026, 4, 15), 1, 1), xy=np.array([[0.0, 0.0], [60.0, 0.0], [-60.0, 0.0]]),
                     spacing_m=70.0, radius_m=112.0)
    fires = Fires(active=(Fire(id=0, x=0.0, y=1.0, t0=0),), new=(0,))
    gs = GrowthStub(smoke_cfg["params"]["growth"], np.random.default_rng(1))
    gs.reset(ctx)
    out = {}
    for mode in ("weather", "per_fire"):
        st = PlumeStub(dict(smoke_cfg["params"]["plume"], wind=mode, intermittency_sigma=0.0), np.random.default_rng(2))
        st.reset(ctx)
        vals = []
        for t, wdir in ((100, 270.0), (101, 90.0)):                          # the weather wind turns round
            ctx.t = t
            src = gs.step((t, fires, None), ctx)
            vals.append(st.step((src, Weather(T=30, RH=30, wind_ms=1.5, wind_dir_deg=wdir)), ctx).c.copy())
        out[mode] = vals
    east, west = 1, 2
    assert out["weather"][0][east] > out["weather"][0][west] and out["weather"][1][west] > out["weather"][1][east]
    a, b = out["per_fire"]
    assert np.sign(a[east] - a[west]) == np.sign(b[east] - b[west])          # the fire keeps its own wind
    lo, hi = smoke_cfg["params"]["plume"]["per_fire_speed_m_min"]
    assert lo <= st._fire_wind[0][2] <= hi


def _short(cfg_path="golden.yaml"):
    return load_config(REPO / "configs" / "experiments" / cfg_path, SHORT)


def test_offline_edge_equals_live_edge():
    cfg, ev, test0, t_total = protocol_config(_short(), 11)
    cfg = copy.deepcopy(cfg)
    cfg["params"]["ignition"]["scripted"] = [{"t_min": test0 + 200, "x": 600.0, "y": 600.0}]
    from prahari.core.pipeline import Simulation
    sim = Simulation(cfg)
    sim.prepare()
    rec = ScoreRecorder(t_total, 100, cfg["params"]["cusum"]["cm_z"])
    live = []
    for tick, t in enumerate(sim.clock.minutes()):
        sim.ctx.tick = tick
        env, fuel, *_, x = sim.step_signals(t)
        res, pv, sc, cand = sim.step_node(x)
        rec(t, res, pv, cand)
        _, _, cl, _, _, _, raq, _ = sim.step_edge(t, env, fuel, cand)
        live += [(t, int(a), list(m)) for a, m, d in zip(cl.anchor, cl.members, raq.decide) if d]
    from prahari.core.rng import make_rngs
    off = edge_alarms(rec.cands, edge_stages(cfg, sim.ctx, make_rngs(11)["srp"]), sim.ctx)
    assert off == live and rec.cands
    p = cfg["params"]["cusum"]
    h, _ = tuned_h(rec.S, rec.frac, p["tune_start_min"], p["tune_end_min"], p, p["target_per_node_30d"])
    assert h == sim.slots["cusum"].stage.snapshot()["h"] or abs(h - sim.slots["cusum"].stage._h) < 1e-9
    replay = replay_candidates(rec.S, test0, h, p)
    assert {t: tuple(n) for t, (n, _) in replay.items()} == {t: tuple(n) for t, (n, _) in rec.cands.items() if t >= test0}


def test_ablation_groups_share_passes_where_they_can():
    g = _groups(["P0", "P2", "P2-SCMR", "P2-RAQ", "P2-QCC", "P2-TTC"])
    assert g[()] == ["P2", "P2-SCMR", "P2-RAQ"] and g[(("qcc", "stub"),)] == ["P2-QCC"] and len(g) == 3


def test_short_golden_with_ablations_and_dial(tmp_path):
    cfg = _short()
    s = run_experiment(cfg, "golden", [11], ["P0", "P2", "P2-SCMR", "P2-RAQ"], tmp_path, dial=[1.0, 4.0])
    p2, dial = s["pipelines"]["P2"], s["dial"]
    assert dial[0]["false_incidents_per_month"]["rate"] == p2["false_incidents_per_month"]["rate"]   # r = 1 is P2
    assert [dial[0]["confirmed_within_3h"][k] for k in "kn"] == [p2["confirmed_within_3h"][k] for k in "kn"]
    assert dial[1]["h_per_seed"][0] <= dial[0]["h_per_seed"][0]                  # a higher target lowers h
    assert s["pipelines"]["P2-SCMR"]["false_incidents_per_month"]["rate"] >= p2["false_incidents_per_month"]["rate"]
    combined = json.loads((tmp_path / "summary.json").read_text())
    assert [r["pipeline"] for r in combined["table"]] == ["P0", "P2", "P2-SCMR", "P2-RAQ"]
    assert combined["table"][1]["report"]["false_incidents_per_month"] == 6.4


def test_table_orders_rows_like_the_report():
    row = {"false_incidents_per_month": {"rate": 1.0, "ci95": [0, 2]}, "confirmed_within_3h": {"rate": 0.5, "ci95": [0, 1]}}
    t = table({"P2-RAQ": row, "P0": row, "P2": row}, None)
    assert [r["pipeline"] for r in t] == ["P0", "P2", "P2-RAQ"] and t[2]["label"] == "P2 minus RAQ"
