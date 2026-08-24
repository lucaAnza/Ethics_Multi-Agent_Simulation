"""Utilitarian lane choice based only on visible entities."""

from .base import EthicalDecision, EthicalFramework, EntitySnapshot, PerceptionState
from .evaluation import choose_lower_cost, entity_cost, format_points


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

    def decide(self, state: PerceptionState) -> EthicalDecision:
        """Choose the lane with the lower cost; ties always remain in lane."""
        current_entities = state.get("current_lane_entities", [])
        other_entities = state.get("other_lane_entities", [])
        action, current_cost, other_cost = choose_lower_cost(
            current_entities,
            other_entities,
            self.entity_values,
        )
        reason = (
            f"Current lane has {format_points(-current_cost)} points, "
            f"while the other lane has {format_points(-other_cost)} points"
        )
        return EthicalDecision(action=action, reason=reason)

    def record_decision(self, decision: EthicalDecision) -> None:
        self.decision_history.append([decision.action, decision.reason])

    def reset(self) -> None:
        self.decision_history.clear()

    def summary(
        self,
        casualties: list[EntitySnapshot],
    ) -> list[tuple[str, str]]:
        total_malus = entity_cost(casualties, self.entity_values)
        return [
            ("Total malus", format_points(total_malus)),
            ("Decisions", str(len(self.decision_history))),
        ]
