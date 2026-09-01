"""Provider-neutral request and response schemas."""

from __future__ import annotations

from dataclasses import dataclass


DECISION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["STAY", "CHANGE_LANE"],
        },
        "reason": {
            "type": "string",
            "minLength": 1,
        },
    },
    "required": ["action", "reason"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class PromptPackage:
    """Fully composed, provider-independent input for one LLM request."""

    system_instruction: str
    prompt: str


@dataclass(frozen=True)
class LLMRawResponse:
    """Provider response with both parser input and complete raw payload."""

    text: str
    model: str
    raw_response: str | None = None

    @property
    def response_for_log(self) -> str:
        """Return the richest provider representation available."""
        return self.raw_response if self.raw_response is not None else self.text
