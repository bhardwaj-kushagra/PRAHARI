"""Phase 6 live mode: the FastAPI server streams the same lines as a recording and switches modules between frames.
Skipped when the optional server dependencies (fastapi, httpx) are not installed."""
import json
import sys
import time

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from ..conftest import REPO  # noqa: E402

sys.path.insert(0, str(REPO))
from server.app import app  # noqa: E402


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_scenarios_and_health(client):
    names = {s["name"] for s in client.get("/scenarios").json()}
    assert {"smoke", "node_3day", "node_mature"} <= names
    assert client.post("/run", json={"scenario": "../secrets"}).status_code == 404


def test_live_run_streams_recording_lines_and_switches_modules(client):
    r = client.post("/run", json={"scenario": "smoke", "days": 0.1, "speed": 0}).json()
    assert r["label"] == "SIMULATION" and r["days"] == 0.1
    ok = client.post("/modules", json={"module": "scmr", "state": "stub"})
    assert ok.status_code in (200, 409)                  # 409 only if the fast run already finished
    assert client.post("/modules", json={"module": "weather", "state": "off"}).status_code in (400, 409)
    lines = []
    with client.websocket_connect("/frames") as ws:
        while True:
            msg = json.loads(ws.receive_text())
            lines.append(msg)
            if "footer" in msg:
                break
    assert "header" in lines[0] and lines[0]["header"]["live"] and lines[0]["header"]["label"] == "SIMULATION"
    frames = [m for m in lines if "t" in m]
    assert frames and frames[-1]["t"] == 143 and all(a["t"] < b["t"] for a, b in zip(frames, frames[1:]))
    if ok.status_code == 200:
        assert any(e["type"] == "module_switch" for f in frames for e in f["events"])
    for _ in range(50):
        h = client.get("/health").json()
        if not h["running"]:
            break
        time.sleep(0.05)
    assert h["scenario"] == "smoke" and "cusum" in h["modules"]
