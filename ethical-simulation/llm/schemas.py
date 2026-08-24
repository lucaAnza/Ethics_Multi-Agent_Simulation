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
    """Minimal response contract implemented by every provider adapter."""

    text: str
    model: str
