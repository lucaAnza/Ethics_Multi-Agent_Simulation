from typing import Any

from .base import EthicalFramework


class ConstantFramework(EthicalFramework):
    def decide(self, state: dict[str, Any]) -> str:
        return "continue"
