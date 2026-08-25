"""Factory methods for runtime entities built from scenario definitions."""

from __future__ import annotations

from collections.abc import Mapping
import random
from typing import Any

from .config import DEFAULT_PEDESTRIAN_SPEED, DEFAULT_VEHICLE_SPEED_KMH
from .entities import Car, Pedestrian


class EntityFactory:
    """Translate validated serializable definitions into runtime entities."""

    @staticmethod
    def create_car(definition: Mapping[str, Any], road_y: float) -> Car:
        y_offset = float(definition["y_offset"])
        return Car(
            x=float(definition["x"]),
            y=road_y + y_offset,
            speed=float(
                definition.get("speed", DEFAULT_VEHICLE_SPEED_KMH)
            ),
            lane_index=1 if y_offset >= 0 else 0,
        )

    @staticmethod
    def create_pedestrian(
        definition: Mapping[str, Any],
        road_y: float,
        *,
        rng: random.Random,
    ) -> Pedestrian:
        return Pedestrian(
            x=float(definition["x"]),
            y=road_y + float(definition["y_offset"]),
            model=definition.get("model", "man"),
            label=definition.get("label"),
            action=definition.get("action", "still"),
            speed=float(
                definition.get("speed", DEFAULT_PEDESTRIAN_SPEED)
            ),
            _rng=rng,
        )
