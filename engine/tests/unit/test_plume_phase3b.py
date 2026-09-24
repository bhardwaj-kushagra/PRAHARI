"""Phase 3b tests: Gaussian plume (M11), Briggs σ (M14), sub-canopy wind (M15), calibrate_q, and switching real/stub."""
import copy
from datetime import datetime

import numpy as np
import pytest

from prahari.core import registry
from prahari.core.clock import Clock
from prahari.core.contracts import Fire, Fires, Weather
from prahari.core.context import RunContext
from prahari.fire.gaussian import (PlumeReal, briggs_sigmas, calibrate_q, canopy_wind, gaussian_plume)
from prahari.fire.growth import GrowthStub

from ..helpers import run_cfg

WIND = Weather(T=30, RH=30, wind_ms=1.5, wind_dir_deg=270.0)          # from the west; u_c = 0.6 m/s


def plume_at(cfg, pts, age=100_000, wind=WIND, hour=12):
    p = dict(cfg["params"]["plume"], intermittency_sigma=0.0)
    g = GrowthStub(dict(cfg["params"]["growth"], qmax_lognormal_sigma=0.0), np.random.default_rng(0))
    pl = PlumeReal(p, np.random.default_rng(0))
    ctx = RunContext(clock=Clock(datetime(2026, 4, 15), 1, 1), xy=np.asarray(pts, dtype=float),
                     spacing_m=70.0, radius_m=112.0, t=hour * 60)
    g.reset(ctx)
    pl.reset(ctx)
    src = g.step((age, Fires(active=(Fire(id=0, x=500.0, y=500.0, t0=0),)), wind), ctx)
    return pl.step((src, wind), ctx).c, pl


def test_m14_briggs_sigmas():
    sy, sz = briggs_sigmas(500.0, "C")
    assert sy == pytest.approx(0.11 * 500 / np.sqrt(1.05)) and sz == pytest.approx(0.08 * 500 / np.sqrt(1.1))
    sy, sz = briggs_sigmas(1000.0, "E")
    assert sy == pytest.approx(0.06 * 1000 / np.sqrt(1.1)) and sz == pytest.approx(0.03 * 1000 / 1.3)
    assert briggs_sigmas(200.0, "A")[1] == pytest.approx(40.0)
    assert np.all(np.array(briggs_sigmas(3.0, "F")) == 1.0)             # clamped ≥ 1 m below the fitted range


def test_m15_canopy_wind():
    np.testing.assert_allclose(canopy_wind([1.5, 0.5, 5.0], 0.4, 0.5), [0.6, 0.5, 2.0])


def test_calibrate_q_value(smoke_cfg):
    p = smoke_cfg["params"]["plume"]
    q = calibrate_q(2.5, 50.0, "C", 0.6, p["receptor_height_m"], p["source_height_m"])
    assert q == pytest.approx(125.94, abs=0.05)                           # DER, recorded in the model card
    assert gaussian_plume(q, 50.0, 0.0, 0.6, "C", 2.5, 0.5) == pytest.approx(2.5)


def test_acceptance_1_calibrated_downwind_value_equals_legacy(smoke_cfg):
    c, pl = plume_at(smoke_cfg, [[550.0, 500.0]])
    assert pl.stability == "C" and c[0] == pytest.approx(2.5, abs=0.1)     # legacy 2.5 su at 50 m, full growth


def test_acceptance_2_crosswind_profile_is_gaussian_with_tabulated_sigma_y(smoke_cfg):
    sy = float(briggs_sigmas(50.0, "C")[0])
    ys = np.array([0.0, 0.5, 1.0, 1.5, 2.0]) * sy
    c, _ = plume_at(smoke_cfg, [[550.0, 500.0 + y] for y in ys])
    np.testing.assert_allclose(c / c[0], np.exp(-ys ** 2 / (2 * sy * sy)), rtol=1e-3)


def test_upwind_floor_and_near_field_are_finite(smoke_cfg):
    c, _ = plume_at(smoke_cfg, [[450.0, 500.0]])
    assert c[0] == pytest.approx(0.25, abs=0.02)                           # ~10% upwind, as the legacy model
    near = np.array([[500.0 + dx, 500.0 + dy] for dx in (-9, -1, 0, 1, 3, 9) for dy in (-5, 0, 5)])
    c, _ = plume_at(smoke_cfg, near)
    assert np.all(np.isfinite(c)) and c.max() < 50.0                      # SPEC §10 risk: no near-field blow-up


def test_night_class_and_transport_delay(smoke_cfg):
    day, _ = plume_at(smoke_cfg, [[550.0, 500.0]], hour=12)
    night, pl = plume_at(smoke_cfg, [[550.0, 500.0]], hour=2)
    assert pl.stability == "E" and night[0] > day[0]                        # stable air: less vertical mixing
    arrival = 120.0 / (0.6 * 60.0)                                         # M16 with u_c: x / u_c minutes
    before, _ = plume_at(smoke_cfg, [[620.0, 500.0]], age=int(np.floor(arrival)))
    after, _ = plume_at(smoke_cfg, [[620.0, 500.0]], age=int(np.floor(arrival)) + 1)
    assert before[0] == 0.0 and after[0] > 0.0


def test_acceptance_3_switching_real_and_stub(smoke_cfg, tmp_path):
    from ..conftest import SMOKE
    from prahari.core.config import load_config
    base = load_config(SMOKE.parent / "fires_day.yaml", {"run": {"days": 0.65}})
    out = {}
    for state in ("stub", "real"):
        cfg = copy.deepcopy(base)
        cfg["modules"]["plume"] = state
        _, health, rec = run_cfg(cfg, tmp_path / f"{state}.prs.jsonl.gz")
        assert health["plume"]["state"] == state
        card = next(m for m in rec.header["model_card"] if m["model"] == "plume")
        out[state] = (card, rec)
    assert out["real"][0]["equation"].startswith("M11") and out["stub"][0]["equation"].startswith("M12")
    assert out["real"][0]["notes"]["q_cal"] == pytest.approx(125.94, abs=0.05)
    ign = [[e for f in r.frames for e in f["events"] if e["type"] == "ignition"] for _, r in out.values()]
    assert ign[0] == ign[1]                                                # same fires: only the plume differs


class RaisingGaussian(PlumeReal):
    def step(self, inputs, ctx):
        if inputs[0].ids:
            raise RuntimeError("gaussian failed")
        return super().step(inputs, ctx)


def test_failing_gaussian_degrades_to_legacy(smoke_cfg, tmp_path, monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, ("plume", "real"), RaisingGaussian)
    from ..conftest import SMOKE
    from prahari.core.config import load_config
    cfg = load_config(SMOKE.parent / "fires_day_gaussian.yaml", {"run": {"days": 0.65}})
    _, health, rec = run_cfg(cfg, tmp_path / "r.prs.jsonl.gz")
    assert health["plume"]["state"] == "degraded" and health["plume"]["running"] == "stub"
    assert max(max(f["nodes"]["conc"]) for f in rec.frames) > 0              # the legacy plume carried on
