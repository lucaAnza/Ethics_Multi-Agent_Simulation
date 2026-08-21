from typing import Any

from .base import STAY, EthicalDecision, EthicalFramework


class ConstantFramework(EthicalFramework):
    def decide(
        self,
        state: dict[str, list[dict[str, Any]]],
    ) -> EthicalDecision:
        return EthicalDecision(STAY, "Constant framework keeps the current lane")
