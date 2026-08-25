"""Utilitarian lane choice based only on visible entities."""

from .base import DecisionContext, EthicalDecision, EthicalFramework, EntitySnapshot
from .config import DEFAULT_ENTITIES_VALUES
from .evaluation import choose_lower_cost, entity_cost, format_points


class UtilitarianFramework(EthicalFramework):
    def __init__(self, entity_values: dict[str, float] | None = None) -> None:
        super().__init__()
        self.entity_values = dict(entity_values or DEFAULT_ENTITIES_VALUES)

    def update_entity_values(self, values: dict[str, float]) -> None:
        self.entity_values.update(values)

    def decide(self, context: DecisionContext) -> EthicalDecision:
        """Choose the lane with the lower cost; ties always remain in lane."""
        current_entities = list(context.current_lane_entities)
        other_entities = list(context.other_lane_entities)
        action, current_cost, other_cost = choose_lower_cost(
            current_entities,
            other_entities,
            self.entity_values,
        )
        reason = (
            f"Current lane has {format_points(-current_cost)} points, "
            f"while the other lane has {format_points(-other_cost)} points"
        )
        return EthicalDecision(
            action=action,
            reason=reason,
            details={
                "current_lane_malus": current_cost,
                "other_lane_malus": other_cost,
            },
        )

    def summary(
        self,
        casualties: list[EntitySnapshot],
    ) -> list[tuple[str, str]]:
        total_malus = entity_cost(casualties, self.entity_values)
        return [
            ("Total malus", format_points(total_malus)),
            ("Decisions", str(len(self.decision_history))),
        ]
