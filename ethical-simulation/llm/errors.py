"""Safe user-facing formatting for LLM provider failures."""

from __future__ import annotations

import re


def safe_error_message(error: Exception | str, *, max_length: int = 220) -> str:
    """Return a concise error while redacting common credential formats."""
    message = " ".join((str(error) or type(error).__name__).split())
    message = re.sub(r"AIza[A-Za-z0-9_-]+", "[REDACTED]", message)
    message = re.sub(
        r"(?i)((?:api[_ -]?key|authorization)\s*[:=]\s*)[^\s,;]+",
        r"\1[REDACTED]",
        message,
    )
    message = re.sub(
        r"(?i)(bearer\s+)[A-Za-z0-9._~-]+",
        r"\1[REDACTED]",
        message,
    )
    if len(message) > max_length:
        return message[: max_length - 3].rstrip() + "..."
    return message
