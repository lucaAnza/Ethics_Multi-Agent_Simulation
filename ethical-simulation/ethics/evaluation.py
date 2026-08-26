"""Reusable numerical evaluation helpers for ethical frameworks."""

from __future__ import annotations

from collections.abc import Mapping

from .base import CHANGE_LANE, STAY, EntitySnapshot


def entity_cost(
    entities: list[EntitySnapshot],
    entity_values: Mapping[str, float],
) -> float:
    """Return the configured casualty cost of a visible entity list."""
    return sum(
        entity_values.get(str(entity.get("model", "unknown")), 0.0)
        for entity in entities
    )


def choose_lower_cost(
    current_entities: list[EntitySnapshot],
    other_entities: list[EntitySnapshot],
    entity_values: Mapping[str, float],
) -> tuple[str, float, float]:
    """Choose the least costly lane, keeping the current lane on a tie."""
    current_cost = entity_cost(current_entities, entity_values)
    other_cost = entity_cost(other_entities, entity_values)
    action = CHANGE_LANE if other_cost < current_cost else STAY
    return action, current_cost, other_cost


def format_points(value: float) -> str:
    """Format whole point values without a redundant decimal part."""
    return str(int(value)) if value.is_integer() else f"{value:g}"
