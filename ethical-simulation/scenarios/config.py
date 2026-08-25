"""Static defaults and persistence settings for scenario generation."""

from pathlib import Path
from typing import Any

from simulation.config import (
    DEFAULT_CAR_START_X,
    DEFAULT_PEDESTRIAN_SPEED,
    DEFAULT_VEHICLE_SPEED_KMH,
    LANE_OFFSET,
)


SCENARIO_SETTINGS_PATH = Path(__file__).with_name("scenario_settings.json")
DEFAULT_SCENARIO_NAME = "Scenario 1"
RANDOM_SCENARIO_NAME = "Random Scenario"
DEFAULT_MOVED_PROBABILITY = 0.1
RANDOM_SCENARIO_MIN_ENTITIES = 2
RANDOM_SCENARIO_MAX_ENTITIES = 10
RANDOM_SCENARIO_FIRST_ENTITY_X = 320.0
RANDOM_SCENARIO_END_MARGIN = 190.0
RANDOM_SCENARIO_POSITION_JITTER_RATIO = 0.28
RANDOM_PEDESTRIAN_SPEED_RANGE = (35.0, 65.0)
REMOVED_SCENARIO_NAMES = frozenset({"Scenario Free"})

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
