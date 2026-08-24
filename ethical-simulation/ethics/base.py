"""Stable contract shared by the simulation and ethical strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, TypeAlias


STAY = "STAY"
CHANGE_LANE = "CHANGE_LANE"

EntitySnapshot: TypeAlias = dict[str, Any]
PerceptionState: TypeAlias = dict[str, list[EntitySnapshot]]


@dataclass(frozen=True)
class EthicalDecision:
    """An action selected by a framework and its human-readable rationale."""

    action: str
    reason: str


class EthicalFramework(ABC):
    @abstractmethod
    def decide(self, state: PerceptionState) -> EthicalDecision:
        """Choose between STAY and CHANGE_LANE from the two visible lanes."""
        raise NotImplementedError

    def record_decision(self, decision: EthicalDecision) -> None:
        """Optionally retain a decision in memory."""

    def reset(self) -> None:
        """Clear any per-simulation state owned by the framework."""

    def summary(
        self,
        casualties: list[EntitySnapshot],
    ) -> list[tuple[str, str]]:
        """Return framework-specific rows for the final summary."""
        return []
