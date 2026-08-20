from typing import Any

from .base import EthicalFramework

DEFAULT_PERSON_VALUES = {
    "Child": 30.0,
    "Adult": 10.0,
    "Elderly": 20.0,
    "Custom": 10.0,
}


class UtilitarianFramework(EthicalFramework):
    def __init__(self, person_values: dict[str, float] | None = None) -> None:
        self.person_values = dict(person_values or DEFAULT_PERSON_VALUES)

    def update_person_values(self, values: dict[str, float]) -> None:
        self.person_values.update(values)

    def decide(self, state: dict[str, Any]) -> str:
        """Choose the action with the lowest configured casualty cost."""
        alternatives = state.get("alternatives", [])
        if not alternatives:
            return "continue"

        model_groups = {
            "boy": "Child",
            "girl": "Child",
            "man": "Adult",
            "woman": "Adult",
            "old_man": "Elderly",
            "old_woman": "Elderly",
            "custom": "Custom",
        }

        def cost(alternative: dict[str, Any]) -> float:
            total = 0.0
            for casualty in alternative.get("casualties", []):
                person_type = model_groups.get(casualty.get("model"), "Custom")
                total += self.person_values.get(person_type, 0.0)
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
