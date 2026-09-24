"""Node-layer statistics for the Phase 5 acceptance (SPEC §7): QCC exceedance (M26) and node-local false candidates
under the replay-tuned h (M28), measured on the quiet pass's held-out test days as the report simulation does."""
from __future__ import annotations

import numpy as np

from prahari.detect.prahari.cusum_real import elevated_fraction
from prahari.detect.prahari.tuning import cm_mask


class NodeObserver:
    """Called every tick of the quiet pass with the node layer's outputs; keeps only small running totals."""

    def __init__(self, test0: int, t_total: int, exceed_p: float, cm_z: float):
        self.test0, self.exceed_p, self.cm_z = test0, exceed_p, cm_z
        self.frac = np.zeros(t_total)
        self.cands: list[tuple[int, int]] = []
        self.n_exceed = self.n_p = 0
        self.p_min = 1.0

    def __call__(self, t: int, res, pv, cand) -> None:
        self.frac[t] = elevated_fraction(res.z, self.cm_z)
        if t < self.test0:
            return
        p = pv.p[:, 0]
        self.n_exceed += int((p <= self.exceed_p).sum())         # M26 — exceedance at the nominal level
        self.n_p += p.size
        self.p_min = min(self.p_min, float(p.min()))
        self.cands.extend((t, int(i)) for i in cand.nodes)

    def summary(self, sim, ev: dict) -> dict:
        """Node-layer metrics of one seed (QCC exceedance, false candidates, tuned h) for the report."""
        cp = sim.cfg["params"]["cusum"]
        cm = cm_mask(self.frac, float(cp["cm_frac"]), int(cp["cm_pad_min"]))   # M28 — with hindsight, as the report
        n, days = sim.ctx.n_nodes, float(ev["test_days"])
        local = sum(1 for t, _ in self.cands if not cm[t])
        node = sim.slots["cusum"].stage.snapshot()
        p1t = sim.slots["baseline_p1t"].stage.snapshot()
        return {
            "exceed": self.n_exceed / self.n_p if self.n_p else None,
            "p_min": self.p_min,
            "cand_per_node_30d": len(self.cands) / n / days * 30.0,
            "local_cand_per_node_30d": local / n / days * 30.0,
            "cm_time_frac_test": float(cm[self.test0:].mean()),
            "h": node.get("h"), "h_tuned": node.get("tuned"), "h_at_cap": node.get("at_cap"),
            "p1t_h": p1t.get("h"), "p1t_at_cap": p1t.get("at_cap"),
            "states": {k: sim.slots[k].health.state for k in ("ttc", "qcc", "score", "cusum", "baseline_p1t")},
        }


def summarise_node(rows: list[dict], ev: dict) -> dict:
    """Pooled and per-seed node metrics with the Phase 5 acceptance targets (TGT, from `params.evaluation`)."""
    def col(k):
        return [r[k] for r in rows]
    ex, loc = col("exceed"), col("local_cand_per_node_30d")
    lo, hi = ev["local_cand_target"]
    elo, ehi = ev["exceed_target"]
    return {
        "per_seed": rows,
        "exceed_mean": float(np.mean(ex)),
        "local_cand_mean": float(np.mean(loc)), "local_cand_median": float(np.median(loc)),
        "h_mean": float(np.mean(col("h"))),
        "targets": {"exceed_p": ev["exceed_p"], "exceed": [elo, ehi], "local_cand_per_node_30d": [lo, hi]},
        "pass": {"exceed": bool(elo <= np.mean(ex) <= ehi), "local_cand": bool(lo <= np.mean(loc) <= hi)},
    }
