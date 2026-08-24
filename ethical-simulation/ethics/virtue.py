"""History and reporting state for the LLM-only Virtue Ethics framework."""

from .base import DecisionContext, EthicalDecision, EthicalFramework, EntitySnapshot


class VirtueEthicsFramework(EthicalFramework):
    """Virtue Ethics is intentionally available only through the LLM engine."""

    def decide(self, context: DecisionContext) -> EthicalDecision:
        raise RuntimeError("Virtue Ethics is available only in llm-agent mode")

    def summary(
        self,
        casualties: list[EntitySnapshot],
    ) -> list[tuple[str, str]]:
        return [("Decisions", str(len(self.decision_history)))]
