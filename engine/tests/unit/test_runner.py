"""Failure isolation (SPEC P5): a failing module degrades down its fallback chain; the run always completes."""
import copy

import numpy as np

from prahari.core import registry
from prahari.detect.prahari.qcc import QCCOff, QCCStub
from prahari.fire.plume import PlumeStub
from prahari.sensors.mox import SensorStub

from ..helpers import run_cfg


def short(cfg, days=0.25):
    cfg = copy.deepcopy(cfg)
    cfg["run"]["days"] = days
    return cfg


class RaisingQCC(QCCStub):
    def step(self, res, ctx):
        if ctx.t >= 100:
            raise RuntimeError("forced failure for the isolation test")
        return super().step(res, ctx)


class NaNPlume(PlumeStub):
    def step(self, inputs, ctx):
        out = super().step(inputs, ctx)
        out.c[0] = np.nan
        return out


class RaisingSensor(SensorStub):
    def step(self, inputs, ctx):
        if ctx.t >= 50:
            raise RuntimeError("sensor died")
        return super().step(inputs, ctx)


def test_forced_stub_exception_degrades_and_run_completes(smoke_cfg, tmp_path, monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, ("qcc", "stub"), RaisingQCC)
    cfg = short(smoke_cfg)
    sim, health, rec = run_cfg(cfg, tmp_path / "r.prs.jsonl.gz")
    h = health["qcc"]
    assert h["state"] == "degraded" and h["running"] == "off"
    assert h["errors"] == 1 and h["degraded_at"] == 100 and "forced failure" in h["last_error"]
    assert rec.frames[-1]["t"] == sim.clock.n_ticks - 1                    # ran to the end
    assert rec.frames[-1]["health"]["qcc"] == "degraded"
    assert rec.footer["health"]["qcc"]["state"] == "degraded"
    events = [e for f in rec.frames for e in f["events"] if e["type"] == "degraded"]
    assert events == [{"type": "degraded", "module": "qcc",
                       "error": "RuntimeError: forced failure for the isolation test"}]
    assert isinstance(sim.slots["qcc"].stage, QCCOff)


def test_nan_output_is_rejected_and_falls_back(smoke_cfg, tmp_path, monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, ("plume", "stub"), NaNPlume)
    cfg = short(smoke_cfg, days=0.65)                                      # includes the 14:00 fire
    _, health, rec = run_cfg(cfg, tmp_path / "r.prs.jsonl.gz")
    assert health["plume"]["state"] == "degraded" and health["plume"]["running"] == "off"
    assert "NaN" in health["plume"]["last_error"]
    for f in rec.frames:
        assert all(np.isfinite(f["nodes"]["reading"]))


def test_required_module_holds_last_valid_output(smoke_cfg, tmp_path, monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, ("sensor", "stub"), RaisingSensor)
    sim, health, rec = run_cfg(short(smoke_cfg), tmp_path / "r.prs.jsonl.gz")
    assert health["sensor"]["state"] == "degraded" and health["sensor"]["running"] == "hold"
    assert health["sensor"]["errors"] == 1                                 # not retried every tick
    assert rec.frames[-1]["t"] == sim.clock.n_ticks - 1


def test_real_falls_back_to_stub_while_no_real_exists(smoke_cfg, tmp_path):
    cfg = short(smoke_cfg, days=0.05)
    cfg["modules"]["growth"] = "real"                 # no real growth model (M10 not built); was energy, then satellite
    _, health, rec = run_cfg(cfg, tmp_path / "r.prs.jsonl.gz")
    assert health["growth"]["requested"] == "real" and health["growth"]["state"] == "stub"
    assert rec.header["modules"]["growth"] == "real"


# -- Phase 1 setup modules --------------------------------------------------------
from prahari.world.siting import SitingReal  # noqa: E402


class RaisingSiting(SitingReal):
    def step(self, inputs, ctx):
        raise RuntimeError("siting failed")


def test_failing_real_siting_falls_back_to_the_grid(smoke_cfg, tmp_path, monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, ("siting", "real"), RaisingSiting)
    cfg = short(smoke_cfg, days=0.05)
    cfg["world"]["layout"] = "greedy"
    sim, health, rec = run_cfg(cfg, tmp_path / "r.prs.jsonl.gz")
    assert health["siting"]["state"] == "degraded" and health["siting"]["running"] == "stub"
    assert rec.header["layouts"]["active"] == "grid"
    assert rec.frames[0]["events"][0] == {"type": "degraded", "module": "siting", "error": "RuntimeError: siting failed"}
    assert rec.frames[-1]["t"] == sim.clock.n_ticks - 1


def test_unbuildable_layout_degrades_instead_of_crashing(smoke_cfg, tmp_path):
    cfg = short(smoke_cfg, days=0.05)
    cfg["world"]["layout"] = "corridor"
    cfg["params"]["siting"]["corridor_classes"] = []          # nothing to follow
    _, health, rec = run_cfg(cfg, tmp_path / "r.prs.jsonl.gz")
    assert health["siting"]["state"] == "degraded" and "could not be built" in health["siting"]["last_error"]
    assert rec.header["layouts"]["active"] == "grid"
