import pytest

from prahari.core.config import ConfigError, load_config

from ..conftest import REPO


def write(tmp_path, text):
    (tmp_path / "default.yaml").write_text((REPO / "configs" / "default.yaml").read_text())
    p = tmp_path / "scen.yaml"
    p.write_text(text)
    return p


def test_smoke_loads(smoke_cfg):
    assert smoke_cfg["scenario"]["name"] == "smoke"
    assert smoke_cfg["params"]["ignition"]["scripted"][0]["t_min"] == 840
    assert set(smoke_cfg["modules"].values()) <= {"real", "stub", "off"}


def test_unknown_key_is_an_error(tmp_path):
    with pytest.raises(ConfigError, match="params.plume.decay_lenght_m"):
        load_config(write(tmp_path, "params:\n  plume:\n    decay_lenght_m: 40\n"))


def test_wrong_type_is_an_error(tmp_path):
    with pytest.raises(ConfigError, match="run.days"):
        load_config(write(tmp_path, "run:\n  days: two\n"))


def test_bad_module_state_is_an_error(tmp_path):
    with pytest.raises(ConfigError, match="modules.qcc"):
        load_config(write(tmp_path, "modules:\n  qcc: maybe\n"))


def test_every_param_block_needs_a_tagged_source(tmp_path):
    with pytest.raises(ConfigError, match="params.plume.source"):
        load_config(write(tmp_path, "params:\n  plume:\n    source: 'made up'\n"))
    with pytest.raises(ConfigError, match="params.plume: missing 'source'"):
        load_config(write(tmp_path, "params:\n  plume:\n    source: ''\n"))
