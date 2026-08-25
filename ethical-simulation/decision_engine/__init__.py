"""Decision-engine implementations shared by every ethical framework."""

from typing import TYPE_CHECKING, Any

from .modes import CODE_MODE, IMPLEMENTATION_MODES, LLM_MODE

if TYPE_CHECKING:
    from .engine import (
        CodeDecisionEngine,
        DecisionEngineResult,
        LLMDecisionEngine,
    )

__all__ = [
    "DRIVING",
    "WAITING_FOR_LLM",
    "EXECUTING_DECISION",
    "CodeDecisionEngine",
    "DecisionEngineResult",
    "LLMDecisionEngine",
    "CODE_MODE",
    "LLM_MODE",
    "IMPLEMENTATION_MODES",
]


def __getattr__(name: str) -> Any:
    """Load execution classes lazily, keeping mode constants dependency-free."""
    engine_names = {
        "DRIVING",
        "WAITING_FOR_LLM",
        "EXECUTING_DECISION",
        "CodeDecisionEngine",
        "DecisionEngineResult",
        "LLMDecisionEngine",
    }
    if name in engine_names:
        from . import engine

        return getattr(engine, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
