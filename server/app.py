"""PRAHARI-SIM engine server (SPEC §3.1, §6.1, Phase 6): FastAPI + WebSocket, a thin wrapper over the engine.

    uvicorn server.app:app --reload        # from the repository root; the dashboard's Live panel connects to :8000

Endpoints: GET /scenarios · POST /run · WebSocket /frames · GET /health · POST /modules. Everything streamed is
simulation output (SIM). The dashboard never needs this server: replay from recordings is the default.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from prahari.core import registry
from prahari.core.config import ConfigError, load_config
from server.live import LiveRun

REPO = Path(__file__).resolve().parents[1]
SCENARIOS = REPO / "configs" / "scenarios"
SWITCHABLE = ("ttc", "qcc", "cusum", "scmr", "fisher", "srp", "raq", "escalate", "cluster", "plume")

app = FastAPI(title="PRAHARI-SIM live server", description="All output is SIMULATION (SIM).")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
STATE: dict = {"run": None, "id": 0, "scenario": None}


class RunRequest(BaseModel):
    scenario: str
    seed: int | None = None
    days: float | None = None
    speed: float = 60.0


class ModuleRequest(BaseModel):
    module: str
    state: str


def _dumps(msg: dict) -> str:
    return json.dumps(msg, separators=(",", ":"), allow_nan=False)


@app.get("/scenarios")
def scenarios() -> list[dict]:
    out = []
    for path in sorted(SCENARIOS.glob("*.yaml")):
        try:
            cfg = load_config(path)
        except ConfigError:
            continue
        out.append({"name": path.stem, "description": cfg["scenario"]["description"], "days": cfg["run"]["days"],
                    "seed": cfg["run"]["seed"]})
    return out


@app.post("/run")
def run(req: RunRequest) -> dict:
    path = SCENARIOS / f"{req.scenario}.yaml"
    if not path.is_file() or path.parent != SCENARIOS:
        raise HTTPException(404, f"unknown scenario {req.scenario!r}")
    over = {"run": {k: v for k, v in (("seed", req.seed), ("days", req.days)) if v is not None}}
    try:
        cfg = load_config(path, over if over["run"] else None)
    except ConfigError as exc:
        raise HTTPException(400, str(exc)) from None
    if STATE["run"] is not None:
        STATE["run"].stop()
    STATE["id"] += 1
    STATE["scenario"] = req.scenario
    STATE["run"] = LiveRun(cfg, req.speed).start()
    return {"run": STATE["id"], "scenario": req.scenario, "seed": cfg["run"]["seed"], "days": cfg["run"]["days"],
            "speed": req.speed, "label": "SIMULATION"}


@app.get("/health")
def health() -> dict:
    r = STATE["run"]
    if r is None:
        return {"running": False, "label": "SIMULATION"}
    return {"running": not r.done, "run": STATE["id"], "scenario": STATE["scenario"], "t": r.t, "error": r.error,
            "modules": r.health(), "label": "SIMULATION"}


@app.post("/modules")
def modules(req: ModuleRequest) -> dict:
    r = STATE["run"]
    if r is None or r.done:
        raise HTTPException(409, "no live run")
    if req.module not in SWITCHABLE or req.state not in ("real", "stub", "off"):
        raise HTTPException(400, f"cannot switch {req.module!r} to {req.state!r}")
    if req.state == "off" and not registry.off_allowed(req.module):
        raise HTTPException(400, f"{req.module} cannot be off")
    r.switch(req.module, req.state)
    return {"module": req.module, "state": req.state, "applied": "at the next recorded frame"}


@app.websocket("/frames")
async def frames(ws: WebSocket) -> None:
    await ws.accept()
    r = STATE["run"]
    if r is None:
        await ws.send_text(_dumps({"error": "no live run; POST /run first"}))
        await ws.close()
        return
    i = 0
    try:
        while True:
            for msg in r.since(i):
                await ws.send_text(_dumps(msg))
                i += 1
            if STATE["run"] is not r or (r.done and i >= len(r.messages)):
                break
            await asyncio.sleep(0.05)
        await ws.close()
    except WebSocketDisconnect:
        return
