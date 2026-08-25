"""Static defaults and persistence settings for scenario generation."""

from collections.abc import Mapping
from dataclasses import dataclass
import math
from pathlib import Path
import random
from typing import Any

from simulation.config import (
    DEFAULT_CAR_START_X,
    DEFAULT_DECISION_DISTANCE,
    DEFAULT_MAX_LANE_CHANGES,
    DEFAULT_PEDESTRIAN_SPEED,
    DEFAULT_VEHICLE_SPEED_KMH,
    DEFAULT_VISION_DISTANCE,
    LANE_OFFSET,
    MAX_CONFIGURABLE_DECISION_DISTANCE,
    MAX_CONFIGURABLE_LANE_CHANGES,
    MAX_CONFIGURABLE_VEHICLE_SPEED_KMH,
    MAX_CONFIGURABLE_VISION_DISTANCE,
    MIN_CONFIGURABLE_DECISION_DISTANCE,
    MIN_CONFIGURABLE_VISION_DISTANCE,
)


SCENARIO_SETTINGS_PATH = Path(__file__).with_name("scenario_settings.json")
DEFAULT_SCENARIO_NAME = "Scenario 1"
RANDOM_SCENARIO_NAME = "Random Scenario"
DEFAULT_PEDESTRIAN_MOVEMENT_PROBABILITY = 0.1
RANDOM_SCENARIO_MIN_ENTITIES = 2
RANDOM_SCENARIO_MAX_ENTITIES = 10
RANDOM_SCENARIO_FIRST_ENTITY_X = 320.0
RANDOM_SCENARIO_END_MARGIN = 190.0
RANDOM_SCENARIO_POSITION_JITTER_RATIO = 0.28
RANDOM_PEDESTRIAN_SPEED_RANGE = (35.0, 65.0)
REMOVED_SCENARIO_NAMES = frozenset({"Scenario Free"})
RANDOM_SETTING_VALUE = "random"
RANDOM_VISION_DISTANCE_RANGE = (
    MIN_CONFIGURABLE_VISION_DISTANCE,
    MAX_CONFIGURABLE_VISION_DISTANCE,
)
RANDOM_MAX_SHIFTS_RANGE = (0, MAX_CONFIGURABLE_LANE_CHANGES)
MAX_RANDOM_SCENARIO_ENTITIES = 100
CRAZY_DRIVER_SPEED_KMH = 120.0
DEFAULT_CRAZY_DRIVER_PROBABILITY = 0.1


def _finite_float(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"{field} must be finite")
    return parsed


def _fixed_or_random(value: object, field: str) -> float | None:
    if isinstance(value, str) and value.strip().lower() == RANDOM_SETTING_VALUE:
        return None
    return _finite_float(value, field)


def _integer(value: object, field: str) -> int:
    parsed = _finite_float(value, field)
    if not parsed.is_integer():
        raise ValueError(f"{field} must be an integer")
    return int(parsed)


@dataclass(frozen=True)
class ResolvedRandomScenarioSettings:
    """Seed-resolved vehicle and generator values for one random run."""

    min_entities: int
    max_entities: int
    initial_speed: float
    vision_distance: float
    decision_distance: float
    max_shifts: int
    pedestrian_movement_probability: float


@dataclass(frozen=True)
class RandomScenarioSettings:
    """Persisted settings used to generate every random scenario."""

    min_entities: int = RANDOM_SCENARIO_MIN_ENTITIES
    max_entities: int = RANDOM_SCENARIO_MAX_ENTITIES
    initial_speed: float = DEFAULT_VEHICLE_SPEED_KMH
    vision_distance: float | None = DEFAULT_VISION_DISTANCE
    decision_distance: float = DEFAULT_DECISION_DISTANCE
    max_shifts: int | None = DEFAULT_MAX_LANE_CHANGES
    crazy_driver_probability: float = DEFAULT_CRAZY_DRIVER_PROBABILITY
    pedestrian_movement_probability: float = (
        DEFAULT_PEDESTRIAN_MOVEMENT_PROBABILITY
    )

    def __post_init__(self) -> None:
        if isinstance(self.min_entities, bool) or not isinstance(
            self.min_entities,
            int,
        ):
            raise ValueError("min_entities must be an integer")
        if isinstance(self.max_entities, bool) or not isinstance(
            self.max_entities,
            int,
        ):
            raise ValueError("max_entities must be an integer")
        if not 1 <= self.min_entities <= MAX_RANDOM_SCENARIO_ENTITIES:
            raise ValueError(
                f"min_entities must be between 1 and "
                f"{MAX_RANDOM_SCENARIO_ENTITIES}"
            )
        if not self.min_entities <= self.max_entities <= MAX_RANDOM_SCENARIO_ENTITIES:
            raise ValueError(
                "max_entities must be greater than or equal to min_entities "
                f"and at most {MAX_RANDOM_SCENARIO_ENTITIES}"
            )
        initial_speed = _finite_float(self.initial_speed, "initial_speed")
        if not 0.0 <= initial_speed <= MAX_CONFIGURABLE_VEHICLE_SPEED_KMH:
            raise ValueError(
                "initial_speed must be between 0 and "
                f"{MAX_CONFIGURABLE_VEHICLE_SPEED_KMH:g}"
            )
        vision_distance: float | None = None
        if self.vision_distance is not None:
            vision_distance = _finite_float(
                self.vision_distance,
                "vision_distance",
            )
            if not (
                RANDOM_VISION_DISTANCE_RANGE[0]
                <= vision_distance
                <= RANDOM_VISION_DISTANCE_RANGE[1]
            ):
                raise ValueError(
                    "vision_distance must be between "
                    f"{RANDOM_VISION_DISTANCE_RANGE[0]:g} and "
                    f"{RANDOM_VISION_DISTANCE_RANGE[1]:g} or random"
                )
        decision_distance = _finite_float(
            self.decision_distance,
            "decision_distance",
        )
        if not (
            MIN_CONFIGURABLE_DECISION_DISTANCE
            <= decision_distance
            <= MAX_CONFIGURABLE_DECISION_DISTANCE
        ):
            raise ValueError(
                "decision_distance must be between "
                f"{MIN_CONFIGURABLE_DECISION_DISTANCE:g} and "
                f"{MAX_CONFIGURABLE_DECISION_DISTANCE:g}"
            )
        if vision_distance is not None and decision_distance > vision_distance:
            raise ValueError(
                "decision_distance cannot be greater than vision_distance"
            )
        if self.max_shifts is not None:
            if isinstance(self.max_shifts, bool) or not isinstance(
                self.max_shifts,
                int,
            ):
                raise ValueError("max_shifts must be an integer or random")
            if not (
                RANDOM_MAX_SHIFTS_RANGE[0]
                <= self.max_shifts
                <= RANDOM_MAX_SHIFTS_RANGE[1]
            ):
                raise ValueError(
                    "max_shifts must be between "
                    f"{RANDOM_MAX_SHIFTS_RANGE[0]} and "
                    f"{RANDOM_MAX_SHIFTS_RANGE[1]} or random"
                )
        for field, probability in (
            ("crazy_driver_probability", self.crazy_driver_probability),
            (
                "pedestrian_movement_probability",
                self.pedestrian_movement_probability,
            ),
        ):
            parsed_probability = _finite_float(probability, field)
            if not 0.0 <= parsed_probability <= 1.0:
                raise ValueError(f"{field} must be between 0 and 1")

    @classmethod
    def from_mapping(
        cls,
        raw: Mapping[str, object] | None,
    ) -> "RandomScenarioSettings":
        """Validate a JSON-compatible mapping, using defaults for missing keys."""
        if raw is not None and not isinstance(raw, Mapping):
            raise ValueError("random_scenario must be an object")
        defaults = cls()
        values = raw or {}
        min_entities = _integer(
            values.get("min_entities", defaults.min_entities),
            "min_entities",
        )
        max_entities = _integer(
            values.get("max_entities", defaults.max_entities),
            "max_entities",
        )
        vision_distance = _fixed_or_random(
            values.get("vision_distance", defaults.vision_distance),
            "vision_distance",
        )
        raw_max_shifts = _fixed_or_random(
            values.get("max_shifts", defaults.max_shifts),
            "max_shifts",
        )
        if raw_max_shifts is not None and not raw_max_shifts.is_integer():
            raise ValueError("max_shifts must be an integer or random")
        return cls(
            min_entities=min_entities,
            max_entities=max_entities,
            initial_speed=_finite_float(
                values.get("initial_speed", defaults.initial_speed),
                "initial_speed",
            ),
            vision_distance=vision_distance,
            decision_distance=_finite_float(
                values.get("decision_distance", defaults.decision_distance),
                "decision_distance",
            ),
            max_shifts=None if raw_max_shifts is None else int(raw_max_shifts),
            crazy_driver_probability=_finite_float(
                values.get(
                    "crazy_driver_probability",
                    defaults.crazy_driver_probability,
                ),
                "crazy_driver_probability",
            ),
            pedestrian_movement_probability=_finite_float(
                values.get(
                    "pedestrian_movement_probability",
                    defaults.pedestrian_movement_probability,
                ),
                "pedestrian_movement_probability",
            ),
        )

    def to_dict(self) -> dict[str, int | float | str]:
        """Return the stable representation written to scenario_settings.json."""
        return {
            "min_entities": self.min_entities,
            "max_entities": self.max_entities,
            "initial_speed": self.initial_speed,
            "vision_distance": (
                RANDOM_SETTING_VALUE
                if self.vision_distance is None
                else self.vision_distance
            ),
            "decision_distance": self.decision_distance,
            "max_shifts": (
                RANDOM_SETTING_VALUE if self.max_shifts is None else self.max_shifts
            ),
            "crazy_driver_probability": self.crazy_driver_probability,
            "pedestrian_movement_probability": (
                self.pedestrian_movement_probability
            ),
        }

    def resolve(self, rng: random.Random) -> ResolvedRandomScenarioSettings:
        """Resolve randomizable values once so paired runs remain identical."""
        speed = (
            CRAZY_DRIVER_SPEED_KMH
            if rng.random() < self.crazy_driver_probability
            else self.initial_speed
        )
        vision = (
            rng.randrange(
                int(RANDOM_VISION_DISTANCE_RANGE[0]),
                int(RANDOM_VISION_DISTANCE_RANGE[1]) + 1,
                10,
            )
            if self.vision_distance is None
            else self.vision_distance
        )
        max_shifts = (
            rng.randint(*RANDOM_MAX_SHIFTS_RANGE)
            if self.max_shifts is None
            else self.max_shifts
        )
        decision_distance = min(self.decision_distance, float(vision))
        return ResolvedRandomScenarioSettings(
            min_entities=self.min_entities,
            max_entities=self.max_entities,
            initial_speed=speed,
            vision_distance=float(vision),
            decision_distance=decision_distance,
            max_shifts=max_shifts,
            pedestrian_movement_probability=(
                self.pedestrian_movement_probability
            ),
        )


DEFAULT_RANDOM_SCENARIO_SETTINGS = RandomScenarioSettings()

DEFAULT_SCENARIO_DEFINITIONS: dict[
    str,
    dict[str, list[dict[str, Any]]],
] = {
    DEFAULT_SCENARIO_NAME: {
        "cars": [
            {
                "x": DEFAULT_CAR_START_X,
                "y_offset": -LANE_OFFSET,
                "speed": DEFAULT_VEHICLE_SPEED_KMH,
            }
        ],
        "pedestrians": [
            {
                "x": 720.0,
                "y_offset": -25.0,
                "model": "man",
                "label": None,
                "action": "still",
                "speed": DEFAULT_PEDESTRIAN_SPEED,
            }
        ],
    },
    "Scenario 2": {
        "cars": [
            {
                "x": DEFAULT_CAR_START_X,
                "y_offset": -LANE_OFFSET,
                "speed": DEFAULT_VEHICLE_SPEED_KMH,
            }
        ],
        "pedestrians": [
            {"x": 400.0, "y_offset": 46.0, "model": "man", "label": None},
            {"x": 475.0, "y_offset": 46.0, "model": "woman", "label": None},
            {"x": 550.0, "y_offset": 46.0, "model": "old_man", "label": None},
            {"x": 625.0, "y_offset": 46.0, "model": "old_woman", "label": None},
            {"x": 700.0, "y_offset": 46.0, "model": "boy", "label": None},
            {"x": 775.0, "y_offset": 46.0, "model": "girl", "label": None},
        ],
    },
}
