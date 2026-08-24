"""Rendering-independent simulation statistics."""

from __future__ import annotations

from collections.abc import Iterable

from .entities import Pedestrian


def pedestrian_category(model: str) -> str:
    if model in {"boy", "girl"}:
        return "Child"
    if model in {"old_man", "old_woman"}:
        return "Elderly"
    if model == "custom":
        return "Custom"
    return "Adult"


def casualty_category_counts(
    pedestrians: Iterable[Pedestrian],
) -> dict[str, int]:
    counts = {"Child": 0, "Adult": 0, "Elderly": 0}
    for pedestrian in pedestrians:
        category = pedestrian_category(pedestrian.model)
        counts[category] = counts.get(category, 0) + 1
    return counts
