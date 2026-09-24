"""Release 1.0 hardening: atomic writes, configuration value checks, clear CLI errors, contract type hints and the
live server's request validation. None of these change what the simulator computes (the recordings stay
byte-identical); they make failures clear and safe."""
import gzip
import io
import os
import typing

import pytest

from prahari.cli import main
from prahari.core.config import ConfigError, load_config
from prahari.record.writer import RecordingWriter, write_atomic

from ..conftest import REPO

SMOKE = REPO / "configs" / "scenarios" / "smoke.yaml"


# -- Atomic writes ---------------------------------------------------------------------------------------------
def test_write_atomic_replaces_whole_file_and_leaves_no_temporary(tmp_path):
    f = tmp_path / "a.json"
    write_atomic(f, b"old")
    write_atomic(f, b"new")
    assert f.read_bytes() == b"new" and os.listdir(tmp_path) == ["a.json"]


def test_a_failed_write_keeps_the_previous_file(tmp_path, monkeypatch):
    f = tmp_path / "a.json"
    write_atomic(f, b"previous")

    def boom(*_):
        raise OSError(28, "No space left on device")
    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        write_atomic(f, b"half-written")
    assert f.read_bytes() == b"previous" and os.listdir(tmp_path) == ["a.json"]


def test_write_atomic_refuses_a_directory(tmp_path):
    with pytest.raises(IsADirectoryError):
        write_atomic(tmp_path, b"x")


def test_recording_bytes_are_unchanged_by_the_atomic_writer(tmp_path):
    w = RecordingWriter(tmp_path / "r.prs.jsonl.gz")
    w.header({"schema": "prahari.frame/1"})
    w.frame({"t": 0})
    w.close({"frames": 1})
    raw = io.BytesIO()                                       # the Phase 0 construction (DECISIONS P0-2)
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=6) as gz:
        gz.write(b'{"header":{"schema":"prahari.frame/1"}}\n{"t":0}\n{"footer":{"frames":1}}\n')
    assert (tmp_path / "r.prs.jsonl.gz").read_bytes() == raw.getvalue()


# -- Configuration values --------------------------------------------------------------------------------------
@pytest.mark.parametrize("over, words", [
    ({"run": {"days": 0}}, "run.days: must be > 0"),
    ({"run": {"days": -2}}, "run.days: must be > 0"),
    ({"run": {"tick_minutes": 0}}, "run.tick_minutes"),
    ({"world": {"n_nodes": 7}}, "square number of nodes"),
    ({"world": {"n_nodes": 0}}, "world.n_nodes"),
    ({"world": {"spacing_m": 0}}, "world.spacing_m"),
    ({"world": {"layout": "hexagon"}}, "world.layout"),
    ({"record": {"from_day": 1}}, "record.from_day"),
    ({"record": {"every_k_ticks": 0}}, "record.every_k_ticks"),
])
def test_impossible_values_are_config_errors(over, words):
    with pytest.raises(ConfigError, match=words.replace(".", r"\.")):
        load_config(SMOKE, over)


def test_every_shipped_configuration_still_loads():
    paths = [p for p in (REPO / "configs").rglob("*.yaml") if p.parent.name != "regimes"]
    assert len(paths) >= 26
    for p in paths:
        load_config(p)


def test_unreadable_and_invalid_files_are_config_errors(tmp_path):
    with pytest.raises(ConfigError, match="config file not found"):
        load_config(tmp_path / "missing.yaml")
    (tmp_path / "default.yaml").write_bytes((REPO / "configs" / "default.yaml").read_bytes())
    bad = tmp_path / "bad.yaml"
    bad.write_text("scenario: [unclosed\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid YAML"):
        load_config(bad)


# -- CLI: one line and a non-zero exit, never a traceback ------------------------------------------------------
def test_cli_errors_are_one_line(tmp_path, capsys):
    assert main(["run", "--config", str(tmp_path / "none.yaml"), "--out", str(tmp_path / "x.gz")]) == 2
    assert main(["run", "--config", str(SMOKE), "--out", str(tmp_path), "--days", "0.01"]) == 1   # a folder
    assert main(["run", "--config", str(SMOKE), "--out", str(tmp_path / "x.gz"), "--days", "0"]) == 2
    assert main(["experiment", "--preset", "no-such-preset"]) == 2
    assert main(["energy", "--config", str(tmp_path / "none.yaml"), "--out", str(tmp_path)]) == 2
    err = capsys.readouterr().err
    assert "Traceback" not in err and "unknown preset" in err and "golden" in err
    for bad in (["--seeds", "1,x"], ["--seeds", ","], ["--jobs", "0"]):
        with pytest.raises(SystemExit) as e:
            main(["experiment", "--preset", "golden", *bad])
        assert e.value.code == 2


# -- Contracts and the live server -----------------------------------------------------------------------------
def test_contract_type_hints_resolve():
    import prahari.core.contracts as c
    for name in ("Prior", "Raq", "Clusters", "Delivered", "Readings"):
        typing.get_type_hints(getattr(c, name))


def test_live_server_rejects_negative_speed_and_days():
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    from server.app import app
    client = TestClient(app)
    assert client.post("/run", json={"scenario": "smoke", "speed": -5}).status_code == 422
    assert client.post("/run", json={"scenario": "smoke", "days": 0}).status_code == 422
    assert client.post("/run", json={"scenario": "../etc/passwd"}).status_code == 404
