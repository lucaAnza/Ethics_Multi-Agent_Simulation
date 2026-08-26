"""Stable contract shared by the simulation and ethical strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, TypeAlias

from simulation.entities import PEDESTRIAN_CATEGORY_PLURALS, pedestrian_category


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


@dataclass(frozen=True)
class DecisionContext:
    """The complete and framework-agnostic input for one ethical decision."""

    decision_id: int
    vehicle_position: float
    current_lane_entities: tuple[EntitySnapshot, ...]
    other_lane_entities: tuple[EntitySnapshot, ...]
    lane_changes_remaining: int

    @classmethod
    def from_state(
        cls,
        *,
        decision_id: int,
        vehicle_position: float,
        state: PerceptionState,
        lane_changes_remaining: int,
    ) -> "DecisionContext":
        """Copy simulation perception so decision engines cannot mutate the world."""
        return cls(
            decision_id=decision_id,
            vehicle_position=vehicle_position,
            current_lane_entities=tuple(
                dict(entity) for entity in state.get("current_lane_entities", [])
            ),
            other_lane_entities=tuple(
                dict(entity) for entity in state.get("other_lane_entities", [])
            ),
            lane_changes_remaining=max(0, int(lane_changes_remaining)),
        )

    @property
    def state(self) -> PerceptionState:
        """Compatibility view used by the existing rule/evaluation helpers."""
        return {
            "current_lane_entities": [
                dict(entity) for entity in self.current_lane_entities
            ],
            "other_lane_entities": [
                dict(entity) for entity in self.other_lane_entities
            ],
        }

    def as_payload(self) -> dict[str, Any]:
        """Return the exact serializable context passed to an LLM provider."""
        return {
            "decision_id": self.decision_id,
            "vehicle_position": self.vehicle_position,
            "current_lane_entities": [
                dict(entity) for entity in self.current_lane_entities
            ],
            "other_lane_entities": [
                dict(entity) for entity in self.other_lane_entities
            ],
            "lane_changes_remaining": self.lane_changes_remaining,
        }


class EthicalFramework(ABC):
    def __init__(self) -> None:
        self.decision_history: list[DecisionRecord] = []

    @abstractmethod
    def decide(self, context: DecisionContext) -> EthicalDecision:
        """Choose between STAY and CHANGE_LANE from the shared context."""
        raise NotImplementedError

    @staticmethod
    def _describe_lane(entities: list[EntitySnapshot]) -> str:
        counts: dict[str, int] = {}
        for entity in entities:
            model = str(entity.get("model", "unknown"))
            category = pedestrian_category(model)
            counts[category] = counts.get(category, 0) + 1
        if not counts:
            return "No visible entities"
        descriptions = []
        for category, count in counts.items():
            display_category = (
                category
                if count == 1
                else PEDESTRIAN_CATEGORY_PLURALS.get(category, f"{category}s")
            )
            descriptions.append(f"{count} {display_category}")
        return ", ".join(descriptions)

    def record_decision(
        self,
        decision: EthicalDecision,
        *,
        context: DecisionContext,
    ) -> None:
        """Store a generic context-rich record with optional framework details."""
        rounded_position = round(context.vehicle_position, 2)
        if rounded_position.is_integer():
            rounded_position = int(rounded_position)
        details = dict(decision.details)
        record: DecisionRecord = {
            "decision_id": context.decision_id,
            "position_x": rounded_position,
            "action": decision.action,
            "current_lane_situation": self._describe_lane(
                list(context.current_lane_entities)
            ),
            "other_lane_situation": self._describe_lane(
                list(context.other_lane_entities)
            ),
            "reason": decision.reason,
            "framework_details": details,
        }
        # Promote generic engine metadata so reports do not need to understand
        # the private details emitted by each ethical framework.
        for key in ("mode", "model", "latency_ms", "fallback", "attempts"):
            if key in details:
                record[key] = details[key]
        self.decision_history.append(record)

    def reset(self) -> None:
        """Clear any per-simulation state owned by the framework."""
        self.decision_history.clear()

    def summary(
        self,
        casualties: list[EntitySnapshot],
    ) -> list[tuple[str, str]]:
        """Return framework-specific rows for the final summary."""
        return []
