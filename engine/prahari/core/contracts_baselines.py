"""Baseline-detector contract (SPEC §5.7, Phase 4). Re-exported by `prahari.core.contracts`; additive rules apply."""
from __future__ import annotations

from dataclasses import dataclass

from prahari.core.contract_checks import ContractError


@dataclass(frozen=True)
class BaselineAlarms:
    """A baseline detector this minute: its per-node candidates and its alarms as (node, cluster members) pairs."""
    candidates: tuple = ()      # node ids raising a node-level candidate this tick
    alarms: tuple = ()          # (node, members) network alarms this tick; members is a sorted tuple of node ids

    def validate(self, n: int) -> None:
        for i in self.candidates:
            if not 0 <= int(i) < n:
                raise ContractError(f"baseline candidate {i} out of range")
        for node, members in self.alarms:
            if not 0 <= int(node) < n or not members or any(not 0 <= int(j) < n for j in members):
                raise ContractError(f"baseline alarm ({node}, {members}) out of range")

    @classmethod
    def neutral(cls, n: int) -> "BaselineAlarms":
        return cls()
