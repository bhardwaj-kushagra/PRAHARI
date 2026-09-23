"""PRAHARI edge layer, real implementations — clustering (M30), SCMR (M31), Fisher combination (M32). SPEC §5.9.

Two forms of clustering, chosen by `params.cluster.form`:

- `legacy` (default; the report simulation's `confirm`): every new candidate i forms a cluster of the candidate
  nodes within R of i in the last W minutes, i included; SCMR compares that neighbourhood with the network, and
  candidates within a tick are processed in node order, each seeing the ones before it (DECISIONS N-b).
- `components` (advanced, M30 as written): connected components of the window's candidate nodes linked within R;
  every component holding a new candidate is a cluster; SCMR uses every node within R of any member.

The stubs (one cluster of everything, always pass, Bonferroni) are in `cluster.py`, `scmr.py` and `fisher.py`.
"""
from __future__ import annotations

from collections import deque

import numpy as np
from scipy.stats import chi2

from prahari.core.contracts import Clusters, Delivered, Fisher, Scmr
from prahari.core.registry import Stage, register


def components(nodes: list, nbr) -> list:
    """M30 — connected components of `nodes` under the neighbour relation `nbr` (N, N bool)."""
    left, out = set(nodes), []
    while left:
        stack, comp = [left.pop()], set()
        while stack:
            i = stack.pop()
            comp.add(i)
            near = [j for j in left if nbr[i, j]]
            left.difference_update(near)
            stack.extend(near)
        out.append(sorted(comp))
    return out


def scmr_ratio(n_members: int, n_neigh: int, n_recent: int, n_nodes: int) -> tuple[float, float, float]:
    """M31 — ρ = f_loc / max(f_net, 1/N) with f_loc = members / neighbourhood size, f_net = recent / N."""
    f_loc = n_members / max(n_neigh, 1)
    f_net = n_recent / n_nodes
    return f_loc, f_net, f_loc / max(f_net, 1.0 / n_nodes)


def fisher_combine(p) -> tuple[float, int, float]:
    """M32 — X = −2 Σ ln p_i ~ χ²(2k); returns (X, dof, p_C)."""
    p = np.clip(np.asarray(p, dtype=float), 1e-300, 1.0)
    X = float(-2.0 * np.log(p).sum())
    dof = 2 * p.size
    return X, dof, float(max(chi2.sf(X, dof), 1e-300))


@register("cluster", kind="real")
class ClusterReal(Stage):
    equation = "M30"
    tag = "LIT"
    description = "Candidates within R over the last 30 min (legacy: around each new candidate, as the report)"

    def reset(self, ctx) -> None:
        self._recent: deque = deque()                        # (t, node, p)

    def _prune(self, t: int) -> None:
        w = int(self.params["window_min"])
        while self._recent and self._recent[0][0] < t - w:  # keep candidates with t' ≥ t − W (report simulation)
            self._recent.popleft()

    def _best_p(self, nodes) -> tuple:
        best: dict[int, float] = {}
        for _, i, p in self._recent:
            best[i] = min(p, best.get(i, 1.0))
        return tuple(best[i] for i in nodes)

    def step(self, delivered: Delivered, ctx) -> Clusters:
        t, nbr = ctx.t, ctx.neighbours
        if not delivered.nodes:
            self._prune(t)
            return Clusters()
        members, ps, anchors, n_recent = [], [], [], []
        if self.params["form"] == "legacy":
            for i, p in zip(delivered.nodes, delivered.p):
                self._prune(t)
                self._recent.append((t, int(i), float(p)))
                recent = {j for _, j, _ in self._recent}
                local = tuple(sorted(j for j in recent if nbr[i, j]))
                members.append(local)
                ps.append(self._best_p(local))
                anchors.append(int(i))
                n_recent.append(len(recent))
        else:
            self._prune(t)
            self._recent.extend((t, int(i), float(p)) for i, p in zip(delivered.nodes, delivered.p))
            recent = sorted({j for _, j, _ in self._recent})
            new = set(int(i) for i in delivered.nodes)
            for comp in components(recent, nbr):
                if new.intersection(comp):
                    members.append(tuple(comp))
                    ps.append(self._best_p(comp))
                    anchors.append(-1)
                    n_recent.append(len(recent))
        return Clusters(members=tuple(members), p=tuple(ps), anchor=tuple(anchors), n_recent=tuple(n_recent))

    def recent_nodes(self) -> set:
        return {i for _, i, _ in self._recent}


@register("scmr", kind="real")
class ScmrReal(Stage):
    equation = "M31"
    tag = "LIT"
    description = "Local candidate rate at least 3× the network rate, else held at WATCH"

    def step(self, clusters: Clusters, ctx) -> Scmr:
        nbr, n = ctx.neighbours, ctx.n_nodes
        thr = float(self.params["ratio_min"])
        f_loc, f_net, ratio, passed = [], [], [], []
        anchors = clusters.anchor or (-1,) * len(clusters.members)
        n_rec = clusters.n_recent or tuple(len(set().union(*map(set, clusters.members))) for _ in clusters.members)
        for m, a, nr in zip(clusters.members, anchors, n_rec):
            neigh = nbr[a] if a >= 0 else nbr[list(m)].any(axis=0)   # legacy: around the trigger; M31: around C
            fl, fn, r = scmr_ratio(len(m), int(neigh.sum()), int(nr), n)
            f_loc.append(fl)
            f_net.append(fn)
            ratio.append(r)
            passed.append(bool(r >= thr))
        return Scmr(f_loc=tuple(f_loc), f_net=tuple(f_net), ratio=tuple(ratio), passed=tuple(passed))


@register("fisher", kind="real")
class FisherReal(Stage):
    equation = "M32"
    tag = "DER"
    description = "Fisher combination of the members' candidate p-values (p_i ≈ r·W)"

    def reset(self, ctx) -> None:
        p = self.params
        # M32 — a candidate's p-value is the chance a quiet node raises one in the window: p_i ≈ r ΔT.
        self._p_cand = float(p["rate_per_node_30d"]) / (30.0 * 1440.0) * float(p["window_min"])

    def step(self, clusters: Clusters, ctx) -> Fisher:
        X, dof, pc = [], [], []
        for m in clusters.members:
            x, d, p = fisher_combine(np.full(len(m), self._p_cand))
            X.append(x)
            dof.append(d)
            pc.append(p)
        return Fisher(X=tuple(X), dof=tuple(dof), p_cluster=tuple(pc))

    def snapshot(self) -> dict:
        return {"p_candidate": self._p_cand if hasattr(self, "_p_cand") else None}
