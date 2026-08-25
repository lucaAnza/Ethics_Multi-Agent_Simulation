"""Central factory for deterministic and LLM decision engines."""

from __future__ import annotations

from llm import GeminiClient, LLMClient, PromptBuilder

from .engine import CodeDecisionEngine, LLMDecisionEngine
from .modes import CODE_MODE, LLM_MODE


class DecisionEngineFactory:
    """Build decision engines while keeping provider defaults in one place."""

    @staticmethod
    def create_code() -> CodeDecisionEngine:
        return CodeDecisionEngine()

    @staticmethod
    def create_llm(
        *,
        client: LLMClient | None = None,
        prompt_builder: PromptBuilder | None = None,
        timeout_seconds: float = 30.0,
        max_attempts: int = 2,
    ) -> LLMDecisionEngine:
        return LLMDecisionEngine(
            client=client or GeminiClient(),
            prompt_builder=prompt_builder or PromptBuilder(),
            timeout_seconds=timeout_seconds,
            max_attempts=max_attempts,
        )

    @classmethod
    def create(
        cls,
        implementation: str,
        *,
        client: LLMClient | None = None,
        prompt_builder: PromptBuilder | None = None,
        timeout_seconds: float = 30.0,
        max_attempts: int = 2,
    ) -> CodeDecisionEngine | LLMDecisionEngine:
        """Select the concrete engine from an implementation mode."""
        if implementation == CODE_MODE:
            return cls.create_code()
        if implementation == LLM_MODE:
            return cls.create_llm(
                client=client,
                prompt_builder=prompt_builder,
                timeout_seconds=timeout_seconds,
                max_attempts=max_attempts,
            )
        raise ValueError(f"Unknown decision-engine implementation: {implementation}")
