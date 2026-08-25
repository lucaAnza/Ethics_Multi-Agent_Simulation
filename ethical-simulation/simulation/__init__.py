"""Core state and entities for the simulation."""

from typing import TYPE_CHECKING, Any

from .entity_factory import EntityFactory

if TYPE_CHECKING:
    from .engine import SimulationDecisionEvent, SimulationEngine, SimulationStepResult
    from .world import DetectedIncident, World

__all__ = [
    "DetectedIncident",
    "EntityFactory",
    "SimulationDecisionEvent",
    "SimulationEngine",
    "SimulationStepResult",
    "World",
]


def __getattr__(name: str) -> Any:
    """Load Arcade-dependent world classes only when explicitly requested."""
    if name in {"DetectedIncident", "World"}:
        from .world import DetectedIncident, World

        return {"DetectedIncident": DetectedIncident, "World": World}[name]
    if name in {"SimulationDecisionEvent", "SimulationEngine", "SimulationStepResult"}:
        from .engine import SimulationDecisionEvent, SimulationEngine, SimulationStepResult

        return {
            "SimulationDecisionEvent": SimulationDecisionEvent,
            "SimulationEngine": SimulationEngine,
            "SimulationStepResult": SimulationStepResult,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
