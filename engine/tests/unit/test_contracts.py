"""Every contract validates its neutral output and rejects bad output; every stub and off runs clean."""
import copy
import dataclasses

import numpy as np
import pytest

from prahari.core import contracts as C
from prahari.core import registry
from prahari.core.pipeline import OUTPUT

from ..helpers import run_cfg


@pytest.mark.parametrize("cls", sorted({c for c in OUTPUT.values()}, key=lambda c: c.__name__))
def test_neutral_outputs_validate(cls):
    cls.neutral(5).validate(5)


def test_contracts_reject_nan_shape_and_range():
    with pytest.raises(C.ContractError, match="NaN"):
        C.Concentration(c=np.array([0.0, np.nan])).validate(2)
    with pytest.raises(C.ContractError, match="shape"):
        C.Concentration(c=np.zeros(3)).validate(2)
    with pytest.raises(C.ContractError, match="below"):
        C.Concentration(c=np.array([-1.0, 0.0])).validate(2)
    with pytest.raises(C.ContractError):
        C.PValues(p=np.array([[0.0]]), n_cal=np.zeros(1)).validate(1)
    with pytest.raises(C.ContractError):
        C.Weather(T=30, RH=140, wind_ms=1, wind_dir_deg=0).validate(1)
    with pytest.raises(C.ContractError, match="different lengths"):
        C.Clusters(members=((1, 2),), p=()).validate(5)


def test_contracts_are_frozen():
    w = C.Weather.neutral(1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        w.T = 1.0


def test_every_module_has_a_stub_and_its_documented_off_rule():
    # SPEC §4.2: weather, growth and sensor may not be off; every other module has an off behaviour.
    for name in OUTPUT:
        assert registry.lookup(name, "stub") is not None, name
    assert {n for n in OUTPUT if not registry.off_allowed(n)} == {"weather", "growth", "sensor"}
    with pytest.raises(ValueError, match="not allowed"):
        registry.build("sensor", "off", {}, None)


def short(cfg, days=0.65):
    cfg = copy.deepcopy(cfg)
    cfg["run"]["days"] = days          # still covers the 14:00 ignition
    return cfg


@pytest.mark.parametrize("state", ["stub", "off", "real"])
def test_all_modules_in_one_state_run_without_degrading(smoke_cfg, tmp_path, state):
    cfg = short(smoke_cfg)
    for name in cfg["modules"]:
        cfg["modules"][name] = state if (state != "off" or registry.off_allowed(name)) else "stub"
    _, health, rec = run_cfg(cfg, tmp_path / "r.prs.jsonl.gz")
    assert not [k for k, v in health.items() if v["state"] == "degraded"]
    assert rec.frames and rec.footer["frames"] == len(rec.frames)


def test_setup_modules_have_stubs_and_siting_cannot_be_off():
    from prahari.core.pipeline import SETUP
    for name, cls in SETUP.items():
        assert registry.lookup(name, "stub") is not None and registry.lookup(name, "real") is not None
        cls.neutral(4).validate(4)
    assert {n for n in SETUP if not registry.off_allowed(n)} == {"siting"}


def test_world_contracts_reject_bad_output():
    with pytest.raises(C.ContractError, match="unknown layout"):
        C.Layout(name="spiral", xy=np.zeros((2, 2))).validate(2)
    with pytest.raises(C.ContractError, match="shape"):
        C.Layout(name="grid", xy=np.zeros((3, 2))).validate(2)
    with pytest.raises(C.ContractError, match="sf"):
        C.Links(gateway=np.zeros(1, int), d_m=np.ones(1), pl_db=np.ones(1), prx_dbm=np.ones(1),
                sf=np.array([6])).validate(1)
    with pytest.raises(C.ContractError, match="coincide"):
        C.Links(gateway=np.zeros(1, int), d_m=np.ones(1), pl_db=np.ones(1), prx_dbm=np.ones(1),
                sf=np.array([0])).validate(1)
    with pytest.raises(C.ContractError, match="positive intensity"):
        C.Landscape(cell_m=10, x0=5, y0=5, lam=np.zeros((2, 2)), forest=np.ones((2, 2), bool),
                    width_m=20, height_m=20).validate(0)
