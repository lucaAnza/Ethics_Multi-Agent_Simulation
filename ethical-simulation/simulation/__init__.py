"""Core state and entities for the simulation."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .world import DetectedIncident, World

__all__ = ["DetectedIncident", "World"]


def __getattr__(name: str) -> Any:
    """Load Arcade-dependent world classes only when explicitly requested."""
    if name in {"DetectedIncident", "World"}:
        from .world import DetectedIncident, World

        return {"DetectedIncident": DetectedIncident, "World": World}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
