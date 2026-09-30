"""R2-10 report: false incidents inside and outside haze, per pipeline and knob, on R1's test seeds (descriptive; SIM).

Reads the re-run per-seed files (`results/research/r1b/test/seed*.json`), checks every count and latency against the
registered R1 files (`results/research/test/`), and writes `results/research/r1_haze_split.json`.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from prahari.record.writer import write_text_atomic
from prahari.research.hazesplit import PAD_MIN, active_mask

MONTH_DAYS = 30.0


def _seeds(d: Path) -> list[dict]:
    files = sorted(d.glob("seed*.json"), key=lambda f: int(f.stem[4:]))
    return [json.loads(f.read_text(encoding="utf-8")) for f in files]


def check_against_r1(rerun: list[dict], r1_dir: Path) -> dict:
    """Every pipeline's per-knob false incidents and fire latencies must equal the registered R1 run."""
    bad = []
    for r in rerun:
        a = json.loads((r1_dir / f"seed{r['seed']}.json").read_text(encoding="utf-8"))
        for name, row in a["pipelines"].items():
            b = r["pipelines"][name]
            if row["false_incidents"] != b["false_incidents"] or row["latencies"] != b["latencies"]:
                bad.append((r["seed"], name))
    return {"seeds_checked": len(rerun), "mismatches": bad}


def split(rows: list[dict], T_of) -> dict:
    """Per pipeline and knob: pooled false incidents inside haze (active at the first alarm), inside with the 60-min
    padding, and outside; rates per month over the pooled test days."""
    out = {}
    days = sum(r["test_days"] for r in rows)
    names = rows[0]["pipelines"]
    for name in names:
        K = len(rows[0]["pipelines"][name]["grid"])
        inside = np.zeros(K)
        inside_pad = np.zeros(K)
        total = np.zeros(K)
        for r in rows:
            T = T_of(r)
            m0 = active_mask(r["haze_episodes"], T)
            m1 = active_mask(r["haze_episodes"], T, PAD_MIN)
            for j, starts in enumerate(r["pipelines"][name]["fi_starts"]):
                s = np.asarray(starts, dtype=int)
                total[j] += s.size
                inside[j] += m0[s].sum() if s.size else 0
                inside_pad[j] += m1[s].sum() if s.size else 0
        scale = MONTH_DAYS / days
        out[name] = {"knob": rows[0]["pipelines"][name]["knob"], "grid": rows[0]["pipelines"][name]["grid"],
                     "total_per_month": (total * scale).round(3).tolist(),
                     "inside_per_month": (inside * scale).round(3).tolist(),
                     "outside_per_month": ((total - inside) * scale).round(3).tolist(),
                     "inside_share": np.where(total > 0, inside / np.maximum(total, 1), np.nan).round(3).tolist(),
                     "inside_share_padded": np.where(total > 0, inside_pad / np.maximum(total, 1), np.nan).round(3).tolist(),
                     "floor_total": round(float((total * scale).min()), 3),
                     "floor_outside": round(float(((total - inside) * scale).min()), 3)}
    return out


def fires_by_haze(rows: list[dict], selection: dict, budget: str) -> dict:
    """Detection within 3 h at each pipeline's selected knob, split by whether haze overlaps the fire's first 3 h."""
    out = {}
    for name in rows[0]["pipelines"]:
        j = selection.get(name, {}).get(budget, {}).get("index")
        if j is None:
            continue
        hit = {True: [0, 0], False: [0, 0]}
        for r in rows:
            for lat, ov in zip(r["pipelines"][name]["latencies"][j], r["fires_haze_overlap"]):
                hit[bool(ov)][1] += 1
                hit[bool(ov)][0] += lat is not None
        out[name] = {"overlap": {"detected": hit[True][0], "fires": hit[True][1]},
                     "no_overlap": {"detected": hit[False][0], "fires": hit[False][1]}}
    return out


def write_haze_split(out: Path) -> list[str]:
    """Build r1_haze_split.json from the re-run seeds (R2-10)."""
    out = Path(out)
    rows = _seeds(out / "r1b" / "test")
    chk = check_against_r1(rows, out / "test")
    analysis = json.loads((out / "r1_analysis.json").read_text(encoding="utf-8"))
    T_of = lambda r: int((r["test_days"] + 28) * 1440)                   # noqa: E731 — protocol run length (min)
    test0 = 28 * 1440                                                     # 14 d calibration + 14 d tuning
    haze_time = [sum(max(0, min(b, T_of(r)) - max(a, test0)) for a, b, _ in r["haze_episodes"]) for r in rows]
    res = {"label": "SIMULATION (descriptive, DECISIONS R2-10)", "seeds": [r["seed"] for r in rows],
           "check_against_r1": chk,
           "haze": {"episodes_per_seed_mean": round(float(np.mean([len(r["haze_episodes"]) for r in rows])), 3),
                    "test_time_share": round(float(np.sum(haze_time)) / sum(r["test_days"] * 1440 for r in rows), 4),
                    "fires_overlapping": int(sum(sum(r["fires_haze_overlap"]) for r in rows)),
                    "fires": int(sum(r["n_fires"] for r in rows))},
           "split": split(rows, T_of),
           "fires_by_haze_at_10": fires_by_haze(rows, analysis["selection"], "10")}
    p = out / "r1_haze_split.json"
    write_text_atomic(p, json.dumps(res, indent=1))
    return [str(p)]
