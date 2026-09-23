"""Phase 0 acceptance: speed, determinism and the recording contract."""
import hashlib
import time

from prahari.cli import main, run

from ..conftest import SMOKE
from ..helpers import run_cfg


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_one_day_runs_in_under_5_seconds(tmp_path):
    t0 = time.perf_counter()
    s = run(str(SMOKE), str(tmp_path / "smoke.prs.jsonl.gz"))
    assert time.perf_counter() - t0 < 5.0
    assert s["frames"] > 0 and (tmp_path / "smoke.health.json").is_file()


def test_same_seed_gives_byte_identical_recording(tmp_path):
    a, b, c = tmp_path / "a.prs.jsonl.gz", tmp_path / "b.prs.jsonl.gz", tmp_path / "c.prs.jsonl.gz"
    assert main(["run", "--config", str(SMOKE), "--out", str(a)]) == 0
    assert main(["run", "--config", str(SMOKE), "--out", str(b)]) == 0
    assert main(["run", "--config", str(SMOKE), "--out", str(c), "--seed", "22"]) == 0
    assert sha(a) == sha(b)
    assert sha(a) != sha(c)


def test_recording_contract(smoke_cfg, tmp_path):
    sim, _, rec = run_cfg(smoke_cfg, tmp_path / "r.prs.jsonl.gz")
    h = rec.header
    assert h["schema"] == "prahari.frame/1" and h["label"] == "SIMULATION"
    assert h["seed"] == 11 and h["days"] == 1 and len(h["nodes"]) == 100
    assert {m["model"] for m in h["model_card"]} == set(h["modules"])
    ts = [f["t"] for f in rec.frames]
    assert ts == sorted(ts) and ts[0] == 0 and ts[-1] == 1439
    n = len(h["nodes"])
    for f in rec.frames:
        assert all(len(v) == n for v in f["nodes"].values())
        assert set(f["nodes"]["state"]) <= set(range(6))
    ids = {t["trace_id"] for t in rec.traces}
    for f in rec.frames:
        for e in f["events"]:
            if "trace_id" in e:
                assert e["trace_id"] in ids
        for a in f["alerts"]:
            assert a["trace_id"] in ids


def test_scripted_fire_is_seen_by_nodes_near_it(smoke_cfg, tmp_path):
    _, _, rec = run_cfg(smoke_cfg, tmp_path / "r.prs.jsonl.gz")
    ign = [e for f in rec.frames for e in f["events"] if e["type"] == "ignition"]
    assert len(ign) == 1 and ign[0]["x"] == 300.0
    alerts = [(f["t"], a) for f in rec.frames for a in f["alerts"] if 840 <= f["t"] <= 840 + 180]
    assert alerts, "the stub pipeline should confirm the scripted fire"
    trace = next(t for t in rec.traces if t["trace_id"] == alerts[0][1]["trace_id"])
    assert trace["type"] == "decision" and trace["bayes"]["decision"] is True
    assert trace["explanation"]
