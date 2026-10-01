"""Figures of protocol R2, built only from `results/research/r2_analysis.json` (charter rule 4). Each footer states
SIMULATION, the scenario, seeds and simulated days. Needs the optional `paper` extra (matplotlib)."""
from __future__ import annotations

import json
from pathlib import Path

from prahari.research.figures import GRID, INK, MUTED, SERIES, _plt, _save

# Colour follows the method (fixed order); Mei-med shares Mei's colour, dashed; AR is the neutral context line.
METHODS = ["P2", "P2-med", "P2-medSCMR", "P2-factor", "P2-gate", "Mei", "Mei-med", "AR"]
STYLE = {m: (c, "-") for m, c in zip(METHODS[:6], SERIES)} | {"Mei-med": (SERIES[5], "--"), "AR": (MUTED, ":")}
LABEL = {"P2": "P2 (SCMR)", "P2-med": "median subtraction", "P2-medSCMR": "median + SCMR",
         "P2-factor": "one-factor reference", "P2-gate": "evidence gate", "Mei": "Mei (raw)", "Mei-med": "Mei (median)",
         "AR": "AR(1) chart"}


def _footer(fig, a: dict, sc: str) -> None:
    s = a["scenarios"][sc]
    seeds = s["seeds"]
    fig.text(0.01, 0.005, f"SIMULATION · PRAHARI-SIM, protocol R2 · scenario {sc} · test seeds {seeds[0]}–{seeds[-1]} "
             f"({len(seeds)})\n{s['test_days_per_seed']} simulated test days per seed after 28 d calibration and tuning",
             fontsize=5, color=MUTED, ha="left", va="bottom", linespacing=1.3)


def fig_floor(plt, a: dict, sc: str = "H-mix") -> list[str]:
    """E1/E3 — each method's false-alarm floor (at its selected floor knob), split into incidents starting inside and
    outside haze, with the seed-bootstrap interval of the total."""
    ms = [m for m in METHODS if m in a["scenarios"][sc]["methods"]]
    fig, ax = plt.subplots(figsize=(4.2, 3.0))
    for i, m in enumerate(ms):
        f = a["scenarios"][sc]["methods"][m]["floor_at_selected_knob"]
        d, ci = f["decomposition"], f["false_incidents"]["ci95_bootstrap"]
        c = STYLE[m][0]
        hatch = "////" if STYLE[m][1] == "--" else None
        ax.barh(i, d["outside"], color=c, height=0.6, edgecolor="white", linewidth=1, hatch=hatch)
        ax.barh(i, d["inside"], left=d["outside"], color=c, alpha=0.4, height=0.6, edgecolor="white", linewidth=1,
                hatch=hatch)
        ax.plot(ci, [i, i], color=INK, lw=0.8)
    ax.set_yticks(range(len(ms)), [LABEL[m] for m in ms])
    ax.invert_yaxis()
    ax.set_xlabel("false incidents per month at the floor knob\n(solid: started outside haze · light: inside haze)")
    ax.grid(axis="y", visible=False)
    fig.subplots_adjust(left=0.3, bottom=0.25, right=0.97, top=0.97)
    _footer(fig, a, sc)
    return _save(fig, f"r2_floor_{sc}")


def fig_pareto(plt, a: dict, sc: str = "H-mix", amoc: bool = False) -> list[str]:
    """Pareto fronts: confirmed within 3 h (or, with `amoc`, mean time to confirmation) against false incidents per
    month (log x), with B*."""
    fig, ax = plt.subplots(figsize=(3.5, 3.2))
    if a.get("b_star"):
        ax.axvline(a["b_star"], color=MUTED, lw=0.6, ls=(0, (3, 3)), zorder=0)
    for m in METHODS:
        r = a["scenarios"][sc]["methods"].get(m)
        if not r:
            continue
        pts = [r["amoc"][j] for j in r["pareto"] if r["amoc"][j]["fa_per_month"] > 0]
        c, ls = STYLE[m]
        y = [p["mean_ttc_min"] if amoc else p["det"] for p in pts]
        ax.plot([p["fa_per_month"] for p in pts], y, color=c, ls=ls, marker="o", ms=2.5, label=LABEL[m])
    ax.set_xscale("log")
    from matplotlib.ticker import FuncFormatter, LogLocator
    ax.xaxis.set_major_locator(LogLocator(subs=(1.0, 3.0)))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.xaxis.set_minor_formatter(FuncFormatter(lambda v, _: ""))
    ax.set_xlabel("false incidents per month (network, test seeds)")
    ax.set_ylabel("mean time to confirmation, min (miss = 180)" if amoc else "fires confirmed within 3 h")
    ax.legend(fontsize=5.5, loc="best")
    fig.subplots_adjust(left=0.17, bottom=0.22, right=0.97, top=0.97)
    _footer(fig, a, sc)
    return _save(fig, f"r2_{'amoc' if amoc else 'pareto'}_{sc}")


def fig_scenarios(plt, a: dict) -> list[str]:
    """Each method's own floor (lowest pooled false incidents per month) in every scenario."""
    scs = [s for s in a["scenarios"] if a["scenarios"][s]["methods"]]
    ms = [m for m in METHODS if m != "AR"]
    fig, ax = plt.subplots(figsize=(7.0, 2.8))
    w = 0.8 / len(ms)
    for k, m in enumerate(ms):
        c, ls = STYLE[m]
        vals = [a["scenarios"][s]["methods"][m]["own_floor"]["fa_per_month"] for s in scs]
        ax.bar([i + (k - len(ms) / 2 + 0.5) * w for i in range(len(scs))], vals, width=w * 0.9, color=c,
               hatch="////" if ls == "--" else None, edgecolor="white", linewidth=0.5, label=LABEL[m])
    ax.set_xticks(range(len(scs)), scs)
    ax.set_ylabel("lowest false incidents per month")
    ax.grid(axis="x", visible=False)
    ax.legend(fontsize=5.5, ncol=4, loc="upper left")
    fig.subplots_adjust(left=0.08, bottom=0.18, right=0.99, top=0.97)
    seeds = {s: a["scenarios"][s]["seeds"] for s in scs}
    fig.text(0.01, 0.005, "SIMULATION · PRAHARI-SIM, protocol R2 · " + " · ".join(
        f"{s} seeds {v[0]}–{v[-1]}" for s, v in seeds.items()), fontsize=5, color=MUTED, ha="left", va="bottom")
    return _save(fig, "r2_scenarios")


def write_figures_r2(out: Path) -> list[str]:
    a = json.loads((Path(out) / "r2_analysis.json").read_text(encoding="utf-8"))
    plt = _plt()
    plt.rcParams["grid.color"] = GRID
    paths = []
    if "H-mix" in a["scenarios"]:
        paths += fig_floor(plt, a) + fig_pareto(plt, a) + fig_pareto(plt, a, amoc=True)
    paths += fig_scenarios(plt, a)
    plt.close("all")
    return paths
