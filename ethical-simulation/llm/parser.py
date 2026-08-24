"""Strict parsing at the trust boundary between an LLM and the simulation."""

from __future__ import annotations

import json
from typing import Any

from ethics.base import CHANGE_LANE, STAY, EthicalDecision


class InvalidLLMResponse(ValueError):
    """Raised when provider output does not match the decision contract."""


def parse_decision(text: str) -> EthicalDecision:
    """Validate JSON shape, allowed action, and non-empty rationale."""
    try:
        payload: Any = json.loads(text)
    except (json.JSONDecodeError, TypeError) as error:
        raise InvalidLLMResponse("Response is not valid JSON") from error

    if not isinstance(payload, dict):
        raise InvalidLLMResponse("Response must be a JSON object")
    if set(payload) != {"action", "reason"}:
        raise InvalidLLMResponse("Response must contain only action and reason")

    action = payload.get("action")
    reason = payload.get("reason")
    if action not in {STAY, CHANGE_LANE}:
        raise InvalidLLMResponse("Action must be STAY or CHANGE_LANE")
    if not isinstance(reason, str) or not reason.strip():
        raise InvalidLLMResponse("Reason must be a non-empty string")
    return EthicalDecision(action=action, reason=reason.strip())
