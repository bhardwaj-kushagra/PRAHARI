"""Edge-layer contracts (SPEC §5.9): clusters, SCMR, Fisher, Bayes factors, prior, RAQ, decision.

Re-exported by `prahari.core.contracts`; import them from there. Same additive rules apply.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from prahari.core.contract_checks import ContractError, _num, _same_len


@dataclass(frozen=True)
class Clusters:
    members: tuple = ()      # tuple of sorted node-id tuples, one per cluster
    p: tuple = ()            # matching tuples of node p-values
    anchor: tuple = ()       # Phase 6: per cluster, the triggering node (legacy form) or −1 (M30 components)
    n_recent: tuple = ()     # Phase 6: per cluster, distinct candidate nodes network-wide in the window (M31 f_net)

    def validate(self, n: int) -> None:
        _same_len("clusters", self.members, self.p)
        for extra in (self.anchor, self.n_recent):
            if extra:
                _same_len("clusters", self.members, extra)
        for m, p in zip(self.members, self.p):
            _same_len("cluster", m, p)
            if not m:
                raise ContractError("empty cluster")

    @classmethod
    def neutral(cls, n: int) -> "Clusters":
        return cls()


@dataclass(frozen=True)
class Scmr:
    f_loc: tuple = ()
    f_net: tuple = ()
    ratio: tuple = ()
    passed: tuple = ()

    def validate(self, n: int) -> None:
        _same_len("scmr", self.f_loc, self.f_net, self.ratio, self.passed)
        for v in self.ratio:
            _num("scmr ratio", v, 0.0)

    @classmethod
    def neutral(cls, n: int) -> "Scmr":
        return cls()


@dataclass(frozen=True)
class Fisher:
    X: tuple = ()
    dof: tuple = ()
    p_cluster: tuple = ()

    def validate(self, n: int) -> None:
        _same_len("fisher", self.X, self.dof, self.p_cluster)
        for p in self.p_cluster:
            _num("p_cluster", p, 1e-300, 1.0)

    @classmethod
    def neutral(cls, n: int) -> "Fisher":
        return cls()


@dataclass(frozen=True)
class BayesFactors:
    bf: tuple = ()

    def validate(self, n: int) -> None:
        for v in self.bf:
            _num("bf", v, 0.0)

    @classmethod
    def neutral(cls, n: int) -> "BayesFactors":
        return cls()


@dataclass(frozen=True)
class Prior:
    odds: float
    day_type: str = "dry_busy"   # or "wet_quiet"
    lam: float = 0.0             # M33 integral term, 0 when not modelled
    p_s: float = 0.0             # M8 sustained-ignition probability, 0 when not modelled

    def validate(self, n: int) -> None:
        _num("prior odds", self.odds, 0.0)
        if self.day_type not in ("dry_busy", "wet_quiet"):
            raise ContractError(f"unknown day type {self.day_type}")

    @classmethod
    def neutral(cls, n: int) -> "Prior":
        return cls(odds=1e-4)


@dataclass(frozen=True)
class Raq:
    quorum: int                  # agreeing nodes needed on the current prior
    threshold: float             # C_FA / C_miss
    posterior_odds: tuple = ()
    decide: tuple = ()
    method: str = "fixed quorum (stub)"   # Phase 6: which rule decided — shown in traces

    def validate(self, n: int) -> None:
        _same_len("raq", self.posterior_odds, self.decide)
        _num("quorum", self.quorum, 1)
        _num("threshold", self.threshold, 0.0)

    @classmethod
    def neutral(cls, n: int) -> "Raq":
        return cls(quorum=2, threshold=0.01)


@dataclass(frozen=True)
class Decision:
    OPTIONAL: ClassVar[tuple] = ("incident",)
    levels: tuple = ()           # per cluster: WATCH, CANDIDATE, CONFIRMED, ESCALATED
    new_alert: tuple = ()        # per cluster: True when this tick raises a new alert
    incident: tuple = ()         # Phase 6: per cluster, the tracked incident id (−1 for the stub)

    def validate(self, n: int) -> None:
        _same_len("decision", self.levels, self.new_alert)
        for lv in self.levels:
            if lv not in ("WATCH", "CANDIDATE", "CONFIRMED", "ESCALATED"):
                raise ContractError(f"unknown level {lv}")

    @classmethod
    def neutral(cls, n: int) -> "Decision":
        return cls()
