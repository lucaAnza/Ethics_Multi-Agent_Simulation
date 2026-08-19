from typing import Any

from .base import EthicalFramework


class RossFramework(EthicalFramework):
    def decide(self, state: dict[str, Any]) -> str:
        return "continue"
