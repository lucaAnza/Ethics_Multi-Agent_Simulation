from .base import STAY, EthicalDecision, EthicalFramework, PerceptionState


class RossFramework(EthicalFramework):
    def decide(
        self,
        state: PerceptionState,
    ) -> EthicalDecision:
        return EthicalDecision(STAY, "Ross placeholder keeps the current lane")
