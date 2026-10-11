"""Figures of protocol R4, built only from `results/research/r4_analysis.json` (charter rule 4). Colour follows the
method as in R2/R3; the haze condition is the line style (dashed: no haze). Each footer states SIMULATION, the
scenarios and seeds. Needs the optional `paper` extra (matplotlib)."""
from __future__ import annotations

import json
from pathlib import Path

from prahari.research.figures import INK, MUTED, _plt, _save
from prahari.research.figures_r2 import LABEL, STYLE

METHODS = ["P2", "P2-medSCMR", "P2-gate"]
DOSES = [("H-none", 0.0), ("H-mix-x0.3", 0.3), ("H-mix", 1.0), ("H-mix-x3", 3.0)]


def _footer(fig, a: dict, scenarios, extra: str = "", seeds_max: int | None = None) -> None:
    parts = []
    for sc in scenarios:
        s = [x for x in a["scenarios"][sc]["seeds"] if seeds_max is None or x <= seeds_max]
        parts.append(f"{sc} seeds {s[0]}–{s[-1]} ({len(s)})")
    days = a["scenarios"][scenarios[0]]["test_days_per_seed"]
    lines = ["SIMULATION · PRAHARI-SIM, protocol R4 · " + " · ".join(parts),
             f"{days} simulated test days per seed after 28 d calibration and tuning" + (f" · {extra}" if extra else "")]
    fig.text(0.01, 0.005, "\n".join(lines), fontsize=5, color=MUTED, ha="left", va="bottom", linespacing=1.3)


def _symlog_x(ax) -> None:
    """False incidents per month on a symlog axis, so settings with no false incident stay visible at 0."""
    from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator
    ax.set_xscale("symlog", linthresh=0.1, linscale=0.4)
    ax.set_xlim(-0.01, 40)
    ax.xaxis.set_major_locator(FixedLocator([0, 0.1, 0.3, 1, 3, 10, 30]))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.xaxis.set_minor_locator(NullLocator())


def fig_price(plt, a: dict) -> list[str]:
    """Family P in pictures: per method, the test-seed Pareto front without haze (dashed) and with H-mix haze
    (solid); the vertical line is the primary budget, 1 false incident a month."""
    fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.7), sharey=True)
    for ax, m in zip(axes, METHODS):
        c = STYLE[m][0]
        ax.axvline(a["primary_budget"], color=MUTED, lw=0.6, ls=(0, (3, 3)), zorder=0)
        for sc, ls, lab in (("H-none", "--", "no haze (H-none)"), ("H-mix", "-", "haze (H-mix)")):
            r = a["scenarios"][sc]["methods"][m]
            pts = [r["amoc"][j] for j in r["pareto"]]
            ax.plot([p["fa_per_month"] for p in pts], [p["det"] for p in pts], color=c, ls=ls, marker="o", ms=2.2,
                    lw=1.2, label=lab)
        _symlog_x(ax)
        ax.set_ylim(0, 1)
        ax.set_title(LABEL[m], fontsize=7.5, color=INK)
        ax.set_xlabel("false incidents per month")
    axes[0].set_ylabel("fires confirmed within 3 h")
    axes[0].legend(fontsize=5.5, loc="lower right")
    fig.subplots_adjust(left=0.08, bottom=0.27, right=0.99, top=0.91, wspace=0.08)
    _footer(fig, a, ["H-none", "H-mix"], "Pareto fronts on the test seeds; dashed line: 1 false incident a month")
    return _save(fig, "r4_price")


def fig_dose(plt, a: dict) -> list[str]:
    """Dose–response on seeds 6001–6050: detection at 1 a month (solid: deployment settings; dashed: equal false
    alarms) and the useful floor at the selected setting, against the haze-episode rate."""
    d = a["descriptive"]["dose_response"]
    xs = [x for _, x in DOSES]
    pos = list(range(len(xs)))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.9))
    for m in METHODS:
        c = STYLE[m][0]
        dep = [d[sc]["methods"][m]["det_at_1"] for sc, _ in DOSES]
        eq = [d[sc]["methods"][m]["det_at_equal_fa_1"] for sc, _ in DOSES]
        a1.plot(pos, dep, color=c, ls="-", marker="o", ms=2.5, label=f"{LABEL[m]} · deployment")
        a1.plot(pos, eq, color=c, ls="--", marker="o", ms=2.0, mfc="white", label=f"{LABEL[m]} · equal false alarms")
        uf = [(d[sc]["methods"][m]["useful_floor_at_selected"] or {}).get("fa_per_month") for sc, _ in DOSES]
        a2.plot(pos, uf, color=c, ls="-", marker="o", ms=2.5, label=LABEL[m])
    for ax in (a1, a2):
        ax.set_xticks(pos, [f"×{x:g}" for x in xs])
        ax.set_xlabel("haze-episode rate (×1 = R2's H-mix)")
    a1.set_ylim(0, 1)
    a1.set_ylabel("confirmed within 3 h at 1 a month")
    a1.legend(fontsize=4.8, loc="lower left")
    a2.set_ylabel("useful floor (false incidents/month)")
    a2.set_ylim(bottom=0)
    a2.legend(fontsize=5.5, loc="upper left")
    fig.subplots_adjust(left=0.08, bottom=0.33, right=0.99, top=0.96, wspace=0.28)
    _footer(fig, a, ["H-none", "H-mix-x0.3", "H-mix", "H-mix-x3"],
            "×0.3 and ×3 use H-mix's settings, ×0 H-none's\n"
            "Equal false alarms: 0 = 1 a month not reachable; at ×3 the deployment settings exceed 1 false incident a "
            "month\nUseful floor: the selected setting detecting ≥ 50% on the selection seeds", seeds_max=6050)
    return _save(fig, "r4_dose")


def fig_floors(plt, a: dict) -> list[str]:
    """The useful floor (lowest false incidents among settings detecting ≥ 50% on the selection seeds) without and
    with haze, per method, split into incidents starting inside (light) and outside (solid) haze, with the
    seed-bootstrap interval of the total."""
    fig, ax = plt.subplots(figsize=(4.6, 2.9))
    rows, labels = [], []
    for m in METHODS:
        for sc, tag in (("H-none", "no haze"), ("H-mix", "haze")):
            rows.append((m, sc))
            labels.append(f"{LABEL[m]} · {tag}")
    for i, (m, sc) in enumerate(rows):
        f = a["scenarios"][sc]["floors"][m]["useful_floor"]
        dcm, ci = f["decomposition"], f["false_incidents"]["ci95_bootstrap"]
        c = STYLE[m][0]
        hatch = "////" if sc == "H-none" else None
        ax.barh(i, dcm["outside"], color=c, height=0.6, edgecolor="white", linewidth=1, hatch=hatch)
        ax.barh(i, dcm["inside"], left=dcm["outside"], color=c, alpha=0.4, height=0.6, edgecolor="white", linewidth=1)
        ax.plot(ci, [i, i], color=INK, lw=0.8)
        ax.text(max(ci[1], dcm["total"]) + 0.03, i, f"{dcm['total']:.2f}", va="center", fontsize=5.5, color=INK)
    ax.set_yticks(range(len(rows)), labels)
    ax.invert_yaxis()
    ax.set_xlabel("useful floor: false incidents per month\n(solid: started outside haze · light: inside haze)")
    ax.grid(axis="y", visible=False)
    fig.subplots_adjust(left=0.36, bottom=0.27, right=0.97, top=0.97)
    _footer(fig, a, ["H-none", "H-mix"], "hatched: no haze")
    return _save(fig, "r4_floors")


def write_figures_r4(out: Path, name: str = "r4_analysis.json") -> list[str]:
    a = json.loads((Path(out) / name).read_text(encoding="utf-8"))
    plt = _plt()
    paths = fig_price(plt, a) + fig_dose(plt, a) + fig_floors(plt, a)
    plt.close("all")
    return paths
