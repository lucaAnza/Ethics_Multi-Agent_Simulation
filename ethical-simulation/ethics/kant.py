from typing import Any

from .base import STAY, EthicalDecision, EthicalFramework


class KantFramework(EthicalFramework):
    def decide(
        self,
        state: dict[str, list[dict[str, Any]]],
    ) -> EthicalDecision:
        return EthicalDecision(STAY, "Kant placeholder keeps the current lane")
