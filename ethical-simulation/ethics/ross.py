from typing import Any

from .base import STAY, EthicalDecision, EthicalFramework


class RossFramework(EthicalFramework):
    def decide(
        self,
        state: dict[str, list[dict[str, Any]]],
    ) -> EthicalDecision:
        return EthicalDecision(STAY, "Ross placeholder keeps the current lane")
