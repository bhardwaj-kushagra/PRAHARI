"""Figures of protocol R1, built only from `results/research/r1_*.json` (CLAUDE.md rules 10 and 15). Each figure's
footer states SIMULATION, the seeds and the simulated days. Needs the optional `paper` extra (matplotlib)."""
from __future__ import annotations

import json
from pathlib import Path

from prahari.cli import REPO

FIG_DIR = REPO / "docs" / "research" / "figures"
# Categorical slots in fixed order (the dashboard's validated reference palette, light mode); text stays neutral.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#dcdcd8"
MAIN = ["P0", "P1", "P1t", "AR", "P2"]
LABEL = {"P0": "P0 fixed threshold", "P1": "P1 v1 as written", "P1t": "P1t v1 replay-tuned", "AR": "AR(1) residual chart",
         "P2": "P2 PRAHARI", "P2-SCMR": "− SCMR", "P2-Q2": "fixed quorum 2", "P2-Q3": "fixed quorum 3",
         "P2-med": "median subtraction, no SCMR", "P2-QCC": "− QCC (Gaussian z)", "P2-TTC": "− TTC (slow z)"}


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 8, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                         "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5, "lines.linewidth": 1.5,
                         "legend.frameon": False, "svg.hashsalt": "prahari", "pdf.fonttype": 42})
    return plt


def _footer(fig, a: dict, extra: str = "") -> None:
    s = a["test_seeds"]
    txt = (f"SIMULATION (PRAHARI-SIM 1.0, protocol R1) · test seeds {s[0]}–{s[-1]} ({len(s)}) · "
           f"{a['test_days_per_seed']} simulated test days per seed after 28 d calibration and tuning{extra}")
    fig.text(0.01, 0.005, txt, fontsize=5.5, color=MUTED, ha="left", va="bottom")


def _save(fig, name: str) -> list[str]:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for ext, meta in (("pdf", {"CreationDate": None, "ModDate": None}), ("png", {"Software": None})):
        p = FIG_DIR / f"{name}.{ext}"
        fig.savefig(p, dpi=300, metadata=meta)
        out.append(str(p))
    return out


def fig_operating(plt, a: dict) -> list[str]:
    """F2 — false incidents per month against confirmed within 3 h, every baseline and P2 (log x)."""
    fig, ax = plt.subplots(figsize=(3.5, 2.7))
    for b in a["budgets"]:
        ax.axvline(b, color=MUTED, lw=0.6, ls=(0, (3, 3)), zorder=0)
        ax.text(b, 1.01, f"{b}/month", transform=ax.get_xaxis_transform(), fontsize=6, color=MUTED, ha="center")
    for c, name in zip(SERIES, MAIN):
        cv = [p for p in a["test"][name]["curve"] if p["fa_per_month"] and p["fa_per_month"] > 0]
        cv.sort(key=lambda p: p["fa_per_month"])
        x, y = [p["fa_per_month"] for p in cv], [100 * p["det"] for p in cv]
        ax.plot(x, y, color=c, marker="o", ms=3, label=LABEL[name])
        if name == "P2":
            ax.fill_between(x, [100 * p["det_ci95"][0] for p in cv], [100 * p["det_ci95"][1] for p in cv],
                            color=c, alpha=0.15, lw=0)
    ax.set_xscale("log")
    ax.set_xlabel("False incidents per month (100 nodes)")
    ax.set_ylabel("Fires confirmed within 3 h (%)")
    ax.set_ylim(0, 100)
    ax.legend(fontsize=6, loc="lower right")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    _footer(fig, a, " · band: P2 95% seed-bootstrap interval")
    return _save(fig, "f2_operating_curves")


def fig_time_to_confirm(plt, a: dict, budget: str) -> list[str]:
    """F3 — share of fires confirmed by each minute after ignition, at the budget's selected knobs."""
    fig, ax = plt.subplots(figsize=(3.5, 2.5))
    for c, name in zip(SERIES, MAIN):
        at = a["test"][name]["at_budget"].get(budget, {})
        if not at.get("reachable"):
            continue
        tc = at["time_to_confirm"]
        ax.step(tc["minutes"], [100 * v for v in tc["share"]], where="post", color=c, label=LABEL[name])
    ax.set_xlabel("Minutes after ignition")
    ax.set_ylabel("Fires confirmed (%)")
    ax.set_xlim(0, 180)
    ax.set_ylim(0, 100)
    ax.legend(fontsize=6, loc="upper left")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    _footer(fig, a, f" · operating points chosen on selection seeds for ≤ {budget} false incidents/month")
    return _save(fig, "f3_time_to_confirm")


def fig_ablations(plt, a: dict, budget: str) -> list[str]:
    """F4 — detection at the budget with 95% intervals: P2 and each ablation (one hue; the rows name them)."""
    names = ["P2", "P2-SCMR", "P2-Q2", "P2-Q3", "P2-med", "P2-QCC", "P2-TTC"]
    rows = [(n, a["test"][n]["at_budget"].get(budget, {})) for n in names]
    rows = [(n, r) for n, r in rows if r.get("reachable")]
    fig, ax = plt.subplots(figsize=(3.5, 2.4))
    for y, (n, r) in enumerate(rows):
        lo, hi = r["det_ci95"]
        ax.plot([100 * lo, 100 * hi], [y, y], color=SERIES[0], lw=1.5)
        ax.plot(100 * r["det"], y, "o", color=SERIES[0], ms=4, mec="white", mew=0.8)
        fa = r["false_incidents"]["rate"]
        ax.text(1.01, y, f"{fa:.1f}/mo", transform=ax.get_yaxis_transform(), fontsize=6, color=MUTED, va="center")
    ax.set_yticks(range(len(rows)), [LABEL[n] if n == "P2" else f"P2 {LABEL[n]}" for n, _ in rows], fontsize=6)
    ax.invert_yaxis()
    ax.set_xlabel(f"Confirmed within 3 h at ≤ {budget} false incidents/month (%)")
    ax.grid(axis="y", visible=False)
    fig.tight_layout(rect=(0, 0.04, 0.9, 1))
    _footer(fig, a, " · right: realised test false incidents per month")
    return _save(fig, "f4_ablations")


def fig_sweeps(plt, a: dict, sw: dict, budget: float) -> list[str]:
    """F5 — sensitivity: detection at equal false alarms for P2 and P1t across each swept assumption."""
    dims = {}
    for label in sw:
        if label != "default":
            dims.setdefault(label.split("=")[0], []).append(label)
    fig, axes = plt.subplots(2, 4, figsize=(7.2, 3.6), sharey=True)
    for ax, (dim, labels) in zip(axes.ravel(), dims.items()):
        pts = [("default", "default")] + [(lab.split("=")[1], lab) for lab in labels]
        xs = list(range(len(pts)))
        for c, name in ((SERIES[4 % len(SERIES)], "P2"), (SERIES[2], "P1t")):
            ys = [sw[lab]["pipelines"].get(name, {}).get("det_at_equal_fa") for _, lab in pts]
            ax.plot(xs, [None if v is None else 100 * v for v in ys], marker="o", ms=3, color=c,
                    label=LABEL[name])
        ax.set_xticks(xs, [p[0] for p in pts], fontsize=6)
        ax.set_title(dim, fontsize=7, color=INK)
        ax.set_ylim(0, 100)
    for ax in axes.ravel()[len(dims):]:
        ax.set_visible(False)
    axes[0, 0].set_ylabel(f"Confirmed at {budget:g} FA/month (%)")
    axes[1, 0].set_ylabel(f"Confirmed at {budget:g} FA/month (%)")
    axes[0, 0].legend(fontsize=6, loc="lower left")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    seeds = sw["default"]["seeds"]
    fig.text(0.01, 0.005, f"SIMULATION · sweep seeds {seeds[0]}–{seeds[-1]} · one assumption changed at a time from "
             f"the golden configuration · detection interpolated at {budget:g} false incidents/month",
             fontsize=5.5, color=MUTED)
    return _save(fig, "f5_sensitivity")


def write_figures(out: Path) -> list[str]:
    """All R1 figures from the analysis files in `out`."""
    plt = _plt()
    a = json.loads((Path(out) / "r1_analysis.json").read_text(encoding="utf-8"))
    b = str(a["budgets"][1]) if len(a["budgets"]) > 1 else str(a["budgets"][0])
    files = fig_operating(plt, a) + fig_time_to_confirm(plt, a, b) + fig_ablations(plt, a, b)
    swp = Path(out) / "r1_sweeps.json"
    if swp.is_file():
        files += fig_sweeps(plt, a, json.loads(swp.read_text(encoding="utf-8"))["sweeps"], float(b))
    plt.close("all")
    return files
