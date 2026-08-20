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
        return "continue"
