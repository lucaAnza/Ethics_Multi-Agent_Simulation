"""Synchronous code and non-blocking LLM ethical decision engines."""

from __future__ import annotations

from collections.abc import Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from time import monotonic
from typing import Any

from ethics.base import STAY, DecisionContext, EthicalDecision, EthicalFramework
from llm.base_client import LLMClient
from llm.errors import safe_error_message
from llm.parser import parse_decision
from llm.prompt_builder import PromptBuilder


DRIVING = "DRIVING"
WAITING_FOR_LLM = "WAITING_FOR_LLM"
EXECUTING_DECISION = "EXECUTING_DECISION"


@dataclass(frozen=True)
class DecisionEngineResult:
    """Completed LLM result paired with the immutable request context."""

    framework_name: str
    context: DecisionContext
    decision: EthicalDecision


class CodeDecisionEngine:
    """Adapter that gives deterministic frameworks the shared engine contract."""

    @staticmethod
    def decide(
        framework: EthicalFramework,
        context: DecisionContext,
    ) -> EthicalDecision:
        decision = framework.decide(context)
        return EthicalDecision(
            action=decision.action,
            reason=decision.reason,
            details={**decision.details, "mode": "code"},
        )


class LLMDecisionEngine:
    """Run provider calls off the Arcade thread with retry and safe fallback."""

    def __init__(
        self,
        *,
        client: LLMClient,
        prompt_builder: PromptBuilder,
        timeout_seconds: float = 30.0,
        max_attempts: int = 2,
    ) -> None:
        self.client = client
        self.prompt_builder = prompt_builder
        self.timeout_seconds = max(0.1, float(timeout_seconds))
        self.max_attempts = max(1, int(max_attempts))
        self._executor = ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="ethical-llm",
        )
        self._future: Future[DecisionEngineResult] | None = None
        self._started_at = 0.0
        self._pending_framework = ""
        self._pending_context: DecisionContext | None = None

    @property
    def is_waiting(self) -> bool:
        return self._future is not None

    @property
    def model_name(self) -> str:
        return self.client.model_name

    def submit(
        self,
        *,
        framework_name: str,
        framework_settings: Mapping[str, Any],
        additional_instructions: str,
        context: DecisionContext,
    ) -> bool:
        """Start one decision request and return immediately."""
        if self._future is not None:
            return False
        prompt = self.prompt_builder.build(
            framework_name=framework_name,
            framework_settings=framework_settings,
            additional_instructions=additional_instructions,
            context=context,
        )
        self._started_at = monotonic()
        self._pending_framework = framework_name
        self._pending_context = context
        self._future = self._executor.submit(
            self._generate_with_retries,
            framework_name,
            context,
            prompt,
        )
        return True

    def _generate_with_retries(
        self,
        framework_name: str,
        context: DecisionContext,
        prompt,
    ) -> DecisionEngineResult:
        started_at = monotonic()
        last_error = "Unknown LLM error"
        for attempt in range(1, self.max_attempts + 1):
            try:
                raw_response = self.client.generate(
                    prompt,
                    timeout_seconds=self.timeout_seconds,
                )
                parsed = parse_decision(raw_response.text)
                latency_ms = int(round((monotonic() - started_at) * 1000))
                decision = EthicalDecision(
                    action=parsed.action,
                    reason=parsed.reason,
                    details={
                        "mode": "llm-agent",
                        "model": raw_response.model,
                        "latency_ms": latency_ms,
                        "fallback": False,
                        "attempts": attempt,
                    },
                )
                return DecisionEngineResult(framework_name, context, decision)
            except Exception as error:  # Provider/timeout/parser boundary.
                last_error = safe_error_message(error)

        latency_ms = int(round((monotonic() - started_at) * 1000))
        return self._fallback_result(
            framework_name,
            context,
            latency_ms=latency_ms,
            attempts=self.max_attempts,
            error=last_error,
        )

    def _fallback_result(
        self,
        framework_name: str,
        context: DecisionContext,
        *,
        latency_ms: int,
        attempts: int,
        error: str,
    ) -> DecisionEngineResult:
        return DecisionEngineResult(
            framework_name,
            context,
            EthicalDecision(
                STAY,
                (
                    "LLM Agent could not produce a valid decision: "
                    f"{safe_error_message(error)}. Safe fallback selected STAY."
                ),
                {
                    "mode": "llm-agent",
                    "model": self.client.model_name,
                    "latency_ms": latency_ms,
                    "fallback": True,
                    "attempts": attempts,
                    "llm_error": safe_error_message(error),
                },
            ),
        )

    def poll(self) -> DecisionEngineResult | None:
        """Return a result when ready, including a watchdog timeout fallback."""
        future = self._future
        if future is None:
            return None

        watchdog_seconds = self.timeout_seconds * self.max_attempts + 2.0
        if not future.done() and monotonic() - self._started_at <= watchdog_seconds:
            return None

        if future.done():
            try:
                result = future.result()
            except Exception as error:
                assert self._pending_context is not None
                elapsed_ms = int(round((monotonic() - self._started_at) * 1000))
                result = self._fallback_result(
                    self._pending_framework,
                    self._pending_context,
                    latency_ms=elapsed_ms,
                    attempts=self.max_attempts,
                    error=str(error) or type(error).__name__,
                )
        else:
            future.cancel()
            assert self._pending_context is not None
            elapsed_ms = int(round((monotonic() - self._started_at) * 1000))
            result = self._fallback_result(
                self._pending_framework,
                self._pending_context,
                latency_ms=elapsed_ms,
                attempts=self.max_attempts,
                error="Decision request exceeded the timeout budget",
            )

        self._future = None
        self._pending_framework = ""
        self._pending_context = None
        return result

    def cancel(self) -> None:
        """Discard any pending request result during reset or mode changes."""
        if self._future is not None:
            self._future.cancel()
        self._future = None
        self._pending_framework = ""
        self._pending_context = None

    def close(self) -> None:
        self.cancel()
        self._executor.shutdown(wait=False, cancel_futures=True)
