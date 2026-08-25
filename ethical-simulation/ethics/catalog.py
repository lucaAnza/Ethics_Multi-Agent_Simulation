"""Backward-compatible imports for the framework catalog.

The canonical definitions live in :mod:`ethics.config`.
"""

from .config import (
    CONSTANT,
    DETERMINISTIC_FRAMEWORKS,
    FRAMEWORK_IMPLEMENTATIONS,
    FRAMEWORK_OPTIONS,
    FRAMEWORKS,
    KANT,
    LLM_FRAMEWORKS,
    UTILITARIANISM,
    VIRTUE_ETHICS,
)

__all__ = [
    "CONSTANT",
    "DETERMINISTIC_FRAMEWORKS",
    "FRAMEWORK_IMPLEMENTATIONS",
    "FRAMEWORK_OPTIONS",
    "FRAMEWORKS",
    "KANT",
    "LLM_FRAMEWORKS",
    "UTILITARIANISM",
    "VIRTUE_ETHICS",
]
