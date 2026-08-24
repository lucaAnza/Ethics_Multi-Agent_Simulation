"""Abstract LLM provider contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .schemas import LLMRawResponse, PromptPackage


class LLMClient(ABC):
    """Small interface that keeps decision logic independent from providers."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate(
        self,
        prompt: PromptPackage,
        *,
        timeout_seconds: float,
    ) -> LLMRawResponse:
        """Generate one structured decision or raise a provider error."""
        raise NotImplementedError
