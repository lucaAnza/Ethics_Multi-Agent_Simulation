"""Google Gemini implementation of the provider-neutral LLM contract."""

from __future__ import annotations

import os

from .base_client import LLMClient
from .config import DEFAULT_GEMINI_MODEL, MINIMUM_GEMINI_TIMEOUT_SECONDS
from .schemas import LLMRawResponse, PromptPackage, decision_json_schema


class GeminiClient(LLMClient):
    """Structured-output client backed by the official ``google-genai`` SDK."""

    def __init__(self, model: str = DEFAULT_GEMINI_MODEL) -> None:
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    def generate(
        self,
        prompt: PromptPackage,
        *,
        timeout_seconds: float,
    ) -> LLMRawResponse:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        # Imports remain local so deterministic code mode can still start and
        # explain a missing optional runtime dependency through the fallback.
        try:
            from google import genai
            from google.genai import types
        except ImportError as error:
            raise RuntimeError(
                "The google-genai package is not installed"
            ) from error

        # Gemini rejects manually configured deadlines below ten seconds.
        effective_timeout = max(
            MINIMUM_GEMINI_TIMEOUT_SECONDS,
            float(timeout_seconds),
        )
        timeout_ms = int(effective_timeout * 1000)
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=timeout_ms,
                # Retry policy is owned by LLMDecisionEngine, so a provider
                # request must represent exactly one bounded attempt.
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        try:
            response = client.models.generate_content(
                model=self._model,
                contents=prompt.prompt,
                config=types.GenerateContentConfig(
                    system_instruction=prompt.system_instruction,
                    temperature=0,
                    response_mime_type="application/json",
                    response_json_schema=decision_json_schema(
                        prompt.allowed_actions
                    ),
                    # The simulation never exposes callable tools. Explicitly
                    # disable the SDK default to avoid its AFC loop and warning.
                    automatic_function_calling=(
                        types.AutomaticFunctionCallingConfig(disable=True)
                    ),
                ),
            )
        finally:
            client.close()

        response_text = response.text
        if not response_text:
            raise RuntimeError("Gemini returned an empty response")
        try:
            raw_response = response.model_dump_json(
                indent=2,
                fallback=str,
            )
        except Exception:
            # Preserve the provider result even if a future SDK version adds a
            # field that its Pydantic serializer cannot encode.
            raw_response = repr(response)
        return LLMRawResponse(
            text=response_text,
            model=response.model_version or self._model,
            raw_response=raw_response,
        )
