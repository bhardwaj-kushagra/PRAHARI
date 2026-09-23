"""Command-line interface: `prahari run --config <scenario.yaml> --out <recording.prs.jsonl.gz>`."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from prahari.core.config import ConfigError, load_config
from prahari.core.pipeline import Simulation
from prahari.record.writer import RecordingWriter


def health_path(out: Path) -> Path:
    name = out.name.split(".prs")[0] if ".prs" in out.name else out.stem
    return out.with_name(f"{name}.health.json")


def run(config: str, out: str, seed: int | None = None, days: float | None = None) -> dict:
    overrides: dict = {"run": {}}
    if seed is not None:
        overrides["run"]["seed"] = seed
    if days is not None:
        overrides["run"]["days"] = days
    cfg = load_config(config, overrides if overrides["run"] else None)
    sim = Simulation(cfg)
    writer = RecordingWriter(out)
    t0 = time.perf_counter()
    health = sim.run(writer)
    elapsed = time.perf_counter() - t0
    summary = {"recording": str(out), "seconds": round(elapsed, 3), "frames": writer.n_frames,
               "traces": writer.n_traces, "modules": health}
    health_path(Path(out)).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="prahari", description="PRAHARI-SIM engine (all output is SIMULATION)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run one scenario and write a recording")
    r.add_argument("--config", required=True, help="scenario YAML (composed over configs/default.yaml)")
    r.add_argument("--out", required=True, help="output recording, e.g. recordings/smoke.prs.jsonl.gz")
    r.add_argument("--seed", type=int, default=None, help="override run.seed")
    r.add_argument("--days", type=float, default=None, help="override run.days")
    args = ap.parse_args(argv)
    try:
        s = run(args.config, args.out, args.seed, args.days)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2
    degraded = [k for k, v in s["modules"].items() if v["state"] == "degraded"]
    print(f"wrote {s['recording']}: {s['frames']} frames, {s['traces']} traces in {s['seconds']} s"
          + (f"; DEGRADED: {', '.join(degraded)}" if degraded else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
