from typing import Any

from .base import EthicalFramework


class UtilitarianFramework(EthicalFramework):
    def decide(self, state: dict[str, Any]) -> str:
        return "continue"
