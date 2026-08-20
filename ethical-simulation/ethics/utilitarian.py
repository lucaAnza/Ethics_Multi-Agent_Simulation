from typing import Any

from .base import EthicalFramework

# You can see all the models in simulation/entities.py
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

    def update_entity_values(self, values: dict[str, float]) -> None:
        self.entity_values.update(values)

    def decide(self, state: dict[str, Any]) -> str:
        """Choose the action with the lowest configured casualty cost."""
        alternatives = state.get("alternatives", [])
        if not alternatives:
            return "continue"

        def cost(alternative: dict[str, Any]) -> float:
            total = 0.0
            for casualty in alternative.get("casualties", []):
                entity_model = casualty.get("model", "custom")
                total += self.entity_values.get(entity_model, 0.0)
            return total

        # When outcomes have the same human cost, braking is the safest and
        # least trajectory-changing intervention.
        tie_break_priority = {
            "continue": 0,
            "brake": 1,
            "steer_right": 2,
            "steer_left": 3,
        }
        best = min(
            alternatives,
            key=lambda alternative: (
                cost(alternative),
                tie_break_priority.get(alternative.get("action"), 99),
            ),
        )
        return str(best.get("action", "continue"))
