"""Stable contract shared by the simulation and ethical strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, TypeAlias


STAY = "STAY"
CHANGE_LANE = "CHANGE_LANE"

EntitySnapshot: TypeAlias = dict[str, Any]
PerceptionState: TypeAlias = dict[str, list[EntitySnapshot]]
DecisionRecord: TypeAlias = dict[str, Any]


@dataclass(frozen=True)
class EthicalDecision:
    """An action selected by a framework and its human-readable rationale."""

    action: str
    reason: str
    details: Mapping[str, Any] = field(default_factory=dict)


class EthicalFramework(ABC):
    def __init__(self) -> None:
        self.decision_history: list[DecisionRecord] = []

    @abstractmethod
    def decide(self, state: PerceptionState) -> EthicalDecision:
        """Choose between STAY and CHANGE_LANE from the two visible lanes."""
        raise NotImplementedError

    @staticmethod
    def _describe_lane(entities: list[EntitySnapshot]) -> str:
        categories = {
            "boy": "Child",
            "girl": "Child",
            "man": "Adult",
            "woman": "Adult",
            "old_man": "Elderly",
            "old_woman": "Elderly",
            "custom": "Custom",
        }
        counts: dict[str, int] = {}
        for entity in entities:
            model = str(entity.get("model", "custom"))
            category = categories.get(model, model.replace("_", " ").title())
            counts[category] = counts.get(category, 0) + 1
        if not counts:
            return "No visible entities"
        plurals = {
            "Child": "Children",
            "Adult": "Adults",
            "Elderly": "Elderly",
            "Custom": "Custom",
        }
        descriptions = []
        for category, count in counts.items():
            display_category = category if count == 1 else plurals.get(
                category,
                f"{category}s",
            )
            descriptions.append(f"{count} {display_category}")
        return ", ".join(descriptions)

    def record_decision(
        self,
        decision: EthicalDecision,
        *,
        position_x: float,
        state: PerceptionState,
    ) -> None:
        """Store a generic context-rich record with optional framework details."""
        rounded_position = round(position_x, 2)
        if rounded_position.is_integer():
            rounded_position = int(rounded_position)
        self.decision_history.append(
            {
                "decision_id": len(self.decision_history) + 1,
                "position_x": rounded_position,
                "action": decision.action,
                "current_lane_situation": self._describe_lane(
                    state.get("current_lane_entities", [])
                ),
                "other_lane_situation": self._describe_lane(
                    state.get("other_lane_entities", [])
                ),
                "reason": decision.reason,
                "framework_details": dict(decision.details),
            }
        )

    def reset(self) -> None:
        """Clear any per-simulation state owned by the framework."""
        self.decision_history.clear()

    def summary(
        self,
        casualties: list[EntitySnapshot],
    ) -> list[tuple[str, str]]:
        """Return framework-specific rows for the final summary."""
        return []
