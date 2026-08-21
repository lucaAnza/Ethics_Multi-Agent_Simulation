"""Utilitarian lane choice based only on visible entities."""

from typing import Any

from .base import CHANGE_LANE, STAY, EthicalDecision, EthicalFramework


DEFAULT_ENTITIES_VALUES = {
    "man": 10.0,
    "woman": 10.0,
    "old_man": 20.0,
    "old_woman": 20.0,
    "boy": 30.0,
    "girl": 30.0,
    "custom": 10.0,
}


class UtilitarianFramework(EthicalFramework):
    def __init__(self, entity_values: dict[str, float] | None = None) -> None:
        self.entity_values = dict(entity_values or DEFAULT_ENTITIES_VALUES)
        self.decision_history: list[list[str]] = []

    def update_entity_values(self, values: dict[str, float]) -> None:
        self.entity_values.update(values)

    def _cost(self, entities: list[dict[str, Any]]) -> float:
        return sum(
            self.entity_values.get(str(entity.get("model", "custom")), 0.0)
            for entity in entities
        )

    @staticmethod
    def _format_points(value: float) -> str:
        return str(int(value)) if value.is_integer() else f"{value:g}"

    def decide(self, state: dict[str, list[dict[str, Any]]]) -> EthicalDecision:
        """Choose the lane with the lower cost; ties always remain in lane."""
        current_entities = state.get("current_lane_entities", [])
        other_entities = state.get("other_lane_entities", [])
        current_malus = -self._cost(current_entities)
        other_malus = -self._cost(other_entities)
        action = CHANGE_LANE if other_malus > current_malus else STAY
        reason = (
            f"Current lane has {self._format_points(current_malus)} points, "
            f"while the other lane has {self._format_points(other_malus)} points"
        )
        return EthicalDecision(action=action, reason=reason)

    def record_decision(self, decision: EthicalDecision) -> None:
        self.decision_history.append([decision.action, decision.reason])

    def reset(self) -> None:
        self.decision_history.clear()

    def summary(self, casualties: list[dict[str, Any]]) -> list[tuple[str, str]]:
        total_malus = self._cost(casualties)
        return [
            ("Total malus", self._format_points(total_malus)),
            ("Decisions", str(len(self.decision_history))),
        ]
