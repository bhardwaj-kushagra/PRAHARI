"""Phase 8 tests: LoRa time on air (M39), ALOHA collisions with capture (M40), shadowing and TS011 relays (M38),
store-and-forward, energy budget, harvest and store (M41–M43) — SPEC §9.2 reference values and the Phase 8
acceptance tests."""
import copy
from datetime import datetime

import numpy as np
import pytest

from prahari.comms.lora import collide, node_links, pick_relays, time_on_air
from prahari.comms.lorawan_real import CommsReal
from prahari.comms.pathloss import LinksReal
from prahari.core.clock import Clock
from prahari.core.context import RunContext
from prahari.core.contracts import Candidates, Delivered
from prahari.energy.budget_real import EnergyReal
from prahari.energy.power import daily_budget_wh, next_mode, solar_day_wh, solar_power_w, usable_wh

XY = np.array([(a, b) for a in np.arange(10) * 70.0 + 385 for b in np.arange(10) * 70.0 + 385])
GW = [{"id": "g1", "x": 700.0, "y": 1390.0}]


def ctx_for(days=1.0, links=None):
    c = RunContext(clock=Clock(datetime(2026, 4, 15), days, 1), xy=XY, spacing_m=70.0, radius_m=112.0, gateways=GW)
    c.links = links
    return c


# -- Acceptance 1: M39 ------------------------------------------------------------------------------
def test_m39_time_on_air_reference_values():
    assert time_on_air(24, 7) * 1e3 == pytest.approx(61.7, abs=0.05)
    assert time_on_air(24, 12) * 1e3 == pytest.approx(1482.8, abs=0.1)          # DE on for SF12
    assert time_on_air(24, 12, de=0) < time_on_air(24, 12)


# -- Acceptance 2: M40 against pure ALOHA ------------------------------------------------------------
@pytest.mark.parametrize("G", [0.1, 0.25, 0.5])
def test_m40_aloha_success_within_3_points(G):
    rng = np.random.default_rng(81)                                          # test fixture only
    toa = time_on_air(24, 7)
    span = 3000 * toa / max(G, 0.1)
    n = rng.poisson(G * span / toa)
    lost = collide(rng.uniform(0, span, n), np.full(n, toa), np.zeros(n), np.full(n, 7), np.zeros(n), 6.0)
    assert abs((1 - lost.mean()) - np.exp(-2 * G)) < 0.03


def test_m40_capture_channels_and_sf():
    s, toa = np.array([0.0, 0.01]), np.array([0.06, 0.06])
    assert collide(s, toa, [0, 0], [7, 7], [-100.0, -103.0], 6.0).tolist() == [True, True]
    assert collide(s, toa, [0, 0], [7, 7], [-100.0, -107.0], 6.0).tolist() == [False, True]   # capture
    assert not collide(s, toa, [0, 1], [7, 7], [-100.0, -100.0], 6.0).any()                   # other channel
    assert not collide(s, toa, [0, 0], [7, 8], [-100.0, -100.0], 6.0).any()                   # other SF
    assert not collide([0.0, 0.07], toa, [0, 0], [7, 7], [0.0, 0.0], 6.0).any()               # no overlap


# -- M38: shadowing and relays -----------------------------------------------------------------------
def test_m38_shadowing_off_keeps_phase1_links_and_on_adds_relays(smoke_cfg):
    p = smoke_cfg["params"]["links"]
    base = LinksReal(p, np.random.default_rng(1)).step((XY, GW), ctx_for())
    assert base.relay is None and (base.sf_all[:, 0] == base.sf).all()
    shadow = LinksReal(dict(p, shadowing_sd_db=6.0), np.random.default_rng(1)).step((XY, GW), ctx_for())
    shadow.validate(100)
    lost = shadow.sf == 0
    assert lost.any() and (shadow.relay[lost] >= 0).all() and (shadow.relay[~lost] == -1).all()
    assert (shadow.sf[shadow.relay[lost]] > 0).all()                         # a relay has its own direct link
    x = shadow.pl_db - base.pl_db
    assert 4.0 < x.std() < 8.0                                                # X_σ ~ N(0, 6²)


def test_relays_pick_the_strongest_linked_neighbour(smoke_cfg):
    prx, sf = node_links(XY[:3] * 0 + np.array([[0, 0], [60, 0], [150, 0]]), smoke_cfg["params"]["links"])
    assert sf[0, 1] > 0 and np.isneginf(prx[0, 0])
    assert pick_relays(np.array([0, 7, 7]), prx, sf).tolist() == [1, -1, -1]


# -- Comms stage: delivery, heartbeats, store-and-forward ---------------------------------------------
def comms(params, links, outages=()):
    st = CommsReal(dict(params, outages=list(outages)), np.random.default_rng(5))
    c = ctx_for(links=links)
    st.reset(c)
    return st, c


def test_candidates_are_delivered_and_heartbeats_are_hourly(smoke_cfg):
    links = LinksReal(smoke_cfg["params"]["links"], None).step((XY, GW), ctx_for())
    st, c = comms(smoke_cfg["params"]["comms"], links)
    got, hb = [], 0
    for t in range(60):
        c.t = t
        out = st.step(Candidates(nodes=(3,) if t == 10 else (), p=(1e-3,) if t == 10 else (), G=np.zeros(100), h=1.0), c)
        out.validate(100)
        got += list(out.nodes)
        hb += sum(pk["kind"] == "heartbeat" for pk in out.packets)
    assert got == [3] and hb == 100                                           # one heartbeat per node per hour


def test_store_and_forward_during_an_outage(smoke_cfg):
    links = LinksReal(smoke_cfg["params"]["links"], None).step((XY, GW), ctx_for())
    st, c = comms(smoke_cfg["params"]["comms"], links, [{"gateway": "g1", "t_min": 5, "duration_min": 20}])
    arrivals = {}
    for t in range(40):
        c.t = t
        cand = Candidates(nodes=(7,), p=(1e-3,), G=np.zeros(100), h=1.0) if t == 10 else \
            Candidates(nodes=(), p=(), G=np.zeros(100), h=1.0)
        out = st.step(cand, c)
        if t == 10:
            assert out.queue[7] == 1 and any(pk.get("queued") for pk in out.packets)
        for i in out.nodes:
            arrivals[i] = t
    assert arrivals == {7: 25}                                                # sent when the gateway returns


def test_nodes_that_are_off_do_not_transmit(smoke_cfg):
    links = LinksReal(smoke_cfg["params"]["links"], None).step((XY, GW), ctx_for())
    st, c = comms(smoke_cfg["params"]["comms"], links)
    c.energy_mode = np.full(100, 2)
    tx = 0
    for t in range(60):
        c.t = t
        tx += len(st.step(Candidates(nodes=(3,), p=(1e-3,), G=np.zeros(100), h=1.0), c).packets)
    assert tx == 0


# -- Energy: M41, M42, M43 and acceptance 3 -------------------------------------------------------------
def test_m41_budgets(smoke_cfg):
    p = smoke_cfg["params"]["energy"]
    std = daily_budget_wh(p, "standard", 24, time_on_air(24, 7))
    assert std == pytest.approx(0.415, abs=0.01)                             # BME688 standard scan + ESP32 + LoRa
    assert daily_budget_wh(p, "ulp", 24, time_on_air(24, 7)) == pytest.approx(0.113, abs=0.005)
    mq2 = daily_budget_wh(dict(p, sensor_kind="mq2"), "standard", 24, time_on_air(24, 7))
    assert mq2 == pytest.approx(22.9, abs=0.1) and mq2 / std > 50


def test_m42_half_sine_integrates_to_the_day(smoke_cfg):
    p = smoke_cfg["params"]["energy"]
    e = solar_day_wh(p)
    assert e == pytest.approx(1.5)                                            # 1 W × 5 kWh/m² × 0.3
    w = solar_power_w(np.arange(1440), e)
    assert w.sum() / 60 == pytest.approx(e, rel=1e-3) and w[:360].max() == 0 and w[1080:].max() == 0


def test_m43_reference_store():
    assert usable_wh(3000, 2.7, 1.35, 2) == pytest.approx(4.56, abs=0.01)     # SPEC §9.2


def test_acceptance_3_half_watt_hour_node_lasts_nine_days(smoke_cfg):
    p = dict(smoke_cfg["params"]["energy"], irradiance_kwh_m2_day=0.0, ulp_below=0.0)   # no sun, no ULP saving
    e = EnergyReal(p, np.random.default_rng(3))
    c = ctx_for(days=12)
    e.reset(c)
    e._draw_mw[:] = 0.5 / 24 * 1000                                           # a 0.5 Wh-per-day node (constant draw)
    stop = empty = None
    for t in range(12 * 1440):
        c.t = t
        s = e.step((t, None, Delivered(nodes=(), p=())), c)
        if stop is None and (s.mode == 2).all():
            stop = t / 1440
        if empty is None and (s.soc == 0).all():
            empty = t / 1440
    assert 8.5 <= stop <= 9.5 and 8.5 <= empty <= 9.5                         # 9 ± 0.5 days (to the 5% stop and to 0)


def test_modes_and_hysteresis():
    m = next_mode([0.5, 0.15, 0.04, 0.08, 0.12], [0, 0, 0, 2, 2], 0.2, 0.05, 0.10)
    assert m.tolist() == [0, 1, 2, 2, 1]


def test_cloudy_days_cut_harvest(smoke_cfg):
    p = dict(smoke_cfg["params"]["energy"], cloudy_days=[2], initial_soc=0.5)
    e = EnergyReal(p, np.random.default_rng(4))
    c = ctx_for(days=2)
    e.reset(c)
    gain = []
    for day in (0, 1):
        before = e._e.copy()
        for t in range(day * 1440, day * 1440 + 1440):
            c.t = t
            e.step((t, None, Delivered(nodes=(), p=())), c)
        gain.append(float((e._e - before).mean()))
    load = daily_budget_wh(p, "standard", 0, 0.0)
    assert gain[0] == pytest.approx(1.5 - load, abs=0.02)
    assert 0.1 * 1.5 - load - 0.02 <= gain[1] <= 0.4 * 1.5 - load + 0.02


def test_defaults_leave_comms_and_energy_as_stubs(smoke_cfg):
    cfg = copy.deepcopy(smoke_cfg)
    assert cfg["modules"]["comms"] == "stub" and cfg["modules"]["energy"] == "stub"
    assert cfg["params"]["links"]["shadowing_sd_db"] == 0.0


def test_energy_table_compares_mq2_and_bme688(smoke_cfg):
    from prahari.eval.energy_table import energy_table
    tab = energy_table(smoke_cfg)
    wh = {(r["sensor"], r["mode"]): r["wh_day"] for r in tab["rows"]}
    assert wh[("BME688", "ULP")] < wh[("BME688", "low power")] < wh[("BME688", "standard")] < wh[("MQ-2", "heater on")]
    assert tab["store_wh"] == pytest.approx(4.556, abs=0.001) and tab["harvest_wh_day"]["clear"] == pytest.approx(1.5)


def test_phase8_scenario_is_deterministic(tmp_path):
    from prahari.core.config import load_config

    from ..conftest import REPO
    from ..helpers import run_cfg
    cfg = load_config(REPO / "configs" / "scenarios" / "cloudy_days.yaml")
    cfg["run"]["days"] = 0.5
    a = run_cfg(copy.deepcopy(cfg), tmp_path / "a.prs.jsonl.gz")[2]
    run_cfg(copy.deepcopy(cfg), tmp_path / "b.prs.jsonl.gz")
    assert (tmp_path / "a.prs.jsonl.gz").read_bytes() == (tmp_path / "b.prs.jsonl.gz").read_bytes()
    assert a.header["links"].get("relay") and any(pk.get("kind") == "heartbeat" for f in a.frames for pk in f["packets"])
    assert all("mode" in f["nodes"] and "queue" in f["nodes"] for f in a.frames)
