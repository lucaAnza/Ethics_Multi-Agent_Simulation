"""Rendering-independent simulation statistics."""

from __future__ import annotations

from collections.abc import Iterable

from .entities import (
    DEFAULT_CASUALTY_CATEGORIES,
    PEDESTRIAN_MODEL_INFO,
    Pedestrian,
    pedestrian_category,
)


def casualty_category_counts(
    pedestrians: Iterable[Pedestrian],
) -> dict[str, int]:
    counts = dict.fromkeys(DEFAULT_CASUALTY_CATEGORIES, 0)
    for pedestrian in pedestrians:
        category = pedestrian_category(pedestrian.model)
        counts[category] = counts.get(category, 0) + 1
    return counts


def casualty_entity_counts(
    pedestrians: Iterable[Pedestrian],
) -> dict[str, int]:
    """Count casualties by their specific pedestrian model."""
    counts = dict.fromkeys(PEDESTRIAN_MODEL_INFO, 0)
    for pedestrian in pedestrians:
        counts[pedestrian.model] = counts.get(pedestrian.model, 0) + 1
    return counts
