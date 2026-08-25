"""Scenario validation, persistence, and runtime factories."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
import json
import math
from pathlib import Path
import random
from typing import TYPE_CHECKING, Any

from app_logging import application_logger
from simulation.config import DEFAULT_WINDOW_WIDTH
from simulation.entities import (
    MOVING_PEDESTRIAN_ACTIONS,
    PEDESTRIAN_ACTIONS,
    PEDESTRIAN_MODEL_CYCLE,
    PEDESTRIAN_MODELS,
)

if TYPE_CHECKING:
    from simulation.entities import Car, Pedestrian

from .config import (
    DEFAULT_CAR_START_X,
    DEFAULT_MOVED_PROBABILITY,
    DEFAULT_PEDESTRIAN_SPEED,
    DEFAULT_SCENARIO_DEFINITIONS,
    DEFAULT_VEHICLE_SPEED_KMH,
    LANE_OFFSET,
    RANDOM_SCENARIO_MAX_ENTITIES,
    RANDOM_SCENARIO_MIN_ENTITIES,
    RANDOM_PEDESTRIAN_SPEED_RANGE,
    RANDOM_SCENARIO_END_MARGIN,
    RANDOM_SCENARIO_FIRST_ENTITY_X,
    RANDOM_SCENARIO_NAME,
    RANDOM_SCENARIO_POSITION_JITTER_RATIO,
    REMOVED_SCENARIO_NAMES,
    SCENARIO_SETTINGS_PATH,
)


@dataclass
class Scenario:
    cars: list[Car]
    pedestrians: list[Pedestrian]


def _finite_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def validate_scenario_definitions(
    definitions: object,
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Validate and normalize definitions loaded from disk or the editor."""
    if not isinstance(definitions, Mapping) or not definitions:
        raise ValueError("the scenario catalog must contain at least one scenario")

    normalized: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for raw_name, raw_scenario in definitions.items():
        if not isinstance(raw_name, str) or not raw_name.strip():
            raise ValueError("scenario names must be non-empty strings")
        if raw_name.strip() in REMOVED_SCENARIO_NAMES:
            continue
        if raw_name.strip() == RANDOM_SCENARIO_NAME:
            raise ValueError(f"{RANDOM_SCENARIO_NAME} is a reserved scenario name")
        if not isinstance(raw_scenario, Mapping):
            raise ValueError(f"{raw_name} must be an object")

        raw_cars = raw_scenario.get("cars")
        raw_pedestrians = raw_scenario.get("pedestrians")
        if not isinstance(raw_cars, list) or not raw_cars:
            raise ValueError(f"{raw_name} must contain at least one car")
        if not isinstance(raw_pedestrians, list):
            raise ValueError(f"{raw_name}.pedestrians must be a list")

        cars: list[dict[str, Any]] = []
        for index, raw_car in enumerate(raw_cars):
            if not isinstance(raw_car, Mapping):
                raise ValueError(f"{raw_name}.cars[{index}] must be an object")
            speed = _finite_number(
                raw_car.get("speed", DEFAULT_VEHICLE_SPEED_KMH),
                "speed",
            )
            if speed < 0:
                raise ValueError("car speed cannot be negative")
            cars.append(
                {
                    "x": _finite_number(raw_car.get("x"), "x"),
                    "y_offset": (
                        LANE_OFFSET
                        if _finite_number(raw_car.get("y_offset"), "y_offset") >= 0
                        else -LANE_OFFSET
                    ),
                    "speed": speed,
                }
            )

        pedestrians: list[dict[str, Any]] = []
        for index, raw_person in enumerate(raw_pedestrians):
            if not isinstance(raw_person, Mapping):
                raise ValueError(
                    f"{raw_name}.pedestrians[{index}] must be an object"
                )
            model = raw_person.get("model", "man")
            if model not in PEDESTRIAN_MODELS:
                raise ValueError(f"unsupported pedestrian model: {model}")
            raw_label = raw_person.get("label")
            label = str(raw_label).strip() if raw_label is not None else ""
            action = raw_person.get("action", "still")
            if action not in PEDESTRIAN_ACTIONS:
                raise ValueError(f"unsupported pedestrian action: {action}")
            speed = _finite_number(
                raw_person.get("speed", DEFAULT_PEDESTRIAN_SPEED),
                "speed",
            )
            if speed < 0:
                raise ValueError("pedestrian speed cannot be negative")
            pedestrians.append(
                {
                    "x": _finite_number(raw_person.get("x"), "x"),
                    "y_offset": _finite_number(
                        raw_person.get("y_offset"), "y_offset"
                    ),
                    "model": model,
                    "label": label or None,
                    "action": action,
                    "speed": speed,
                }
            )

        normalized[raw_name.strip()] = {
            "cars": cars,
            "pedestrians": pedestrians,
        }

    if not normalized:
        raise ValueError("the scenario catalog must contain a non-free scenario")
    return normalized


def load_scenario_definitions(
    path: Path = SCENARIO_SETTINGS_PATH,
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Load the persistent catalog, falling back safely to built-in defaults."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        definitions = payload.get("scenarios") if isinstance(payload, dict) else None
        return validate_scenario_definitions(definitions)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        application_logger.log_message(
            f"[SCENARIO SETTINGS] Using defaults: {error}"
        )
        return validate_scenario_definitions(
            deepcopy(DEFAULT_SCENARIO_DEFINITIONS)
        )


def save_scenario_definitions(
    definitions: Mapping[str, Mapping[str, list[dict[str, Any]]]],
    path: Path = SCENARIO_SETTINGS_PATH,
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Validate and atomically save the scenario catalog as JSON."""
    normalized = validate_scenario_definitions(definitions)
    payload = {"version": 2, "scenarios": normalized}
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)
    return normalized


def generate_random_scenario_definition(
    world_width: float,
    *,
    rng: random.Random,
    min_entities: int = RANDOM_SCENARIO_MIN_ENTITIES,
    max_entities: int = RANDOM_SCENARIO_MAX_ENTITIES,
    moved_probability: float = DEFAULT_MOVED_PROBABILITY,
) -> dict[str, list[dict[str, Any]]]:
    """Generate one seeded two-lane scenario as a serializable definition."""
    minimum = max(1, int(min_entities))
    maximum = max(minimum, int(max_entities))
    probability = float(moved_probability)
    if not 0.0 <= probability <= 1.0:
        raise ValueError("moved_probability must be between 0 and 1")

    entity_count = rng.randint(minimum, maximum)
    first_x = RANDOM_SCENARIO_FIRST_ENTITY_X
    last_x = max(first_x + 40.0, float(world_width) - RANDOM_SCENARIO_END_MARGIN)
    slot_width = (last_x - first_x) / entity_count
    positions = [
        first_x
        + slot_width * (index + 0.5)
        + rng.uniform(
            -slot_width * RANDOM_SCENARIO_POSITION_JITTER_RATIO,
            slot_width * RANDOM_SCENARIO_POSITION_JITTER_RATIO,
        )
        for index in range(entity_count)
    ]
    positions.sort()

    models: list[str] = []
    while len(models) < entity_count:
        cycle = list(PEDESTRIAN_MODEL_CYCLE)
        rng.shuffle(cycle)
        if models and cycle[0] == models[-1]:
            swap_index = next(
                index for index, model in enumerate(cycle[1:], start=1)
                if model != models[-1]
            )
            cycle[0], cycle[swap_index] = cycle[swap_index], cycle[0]
        models.extend(cycle)

    pedestrians: list[dict[str, Any]] = []
    for index, (x, model) in enumerate(zip(positions, models)):
        moves = rng.random() < probability
        action = rng.choice(MOVING_PEDESTRIAN_ACTIONS) if moves else "still"
        pedestrians.append(
            {
                "x": round(x, 2),
                "y_offset": rng.choice((-LANE_OFFSET, LANE_OFFSET)),
                "model": model,
                "label": f"Custom {index + 1}" if model == "custom" else None,
                "action": action,
                "speed": (
                    round(rng.uniform(*RANDOM_PEDESTRIAN_SPEED_RANGE), 2)
                    if moves
                    else DEFAULT_PEDESTRIAN_SPEED
                ),
            }
        )

    return {
        "cars": [
            {
                "x": DEFAULT_CAR_START_X,
                "y_offset": -LANE_OFFSET,
                "speed": DEFAULT_VEHICLE_SPEED_KMH,
            }
        ],
        "pedestrians": pedestrians,
    }


def create_scenario(
    name: str,
    road_y: float,
    definitions: Mapping[str, Mapping[str, list[dict[str, Any]]]] | None = None,
    *,
    rng: random.Random | None = None,
    world_width: float = DEFAULT_WINDOW_WIDTH,
    moved_probability: float = DEFAULT_MOVED_PROBABILITY,
) -> Scenario:
    """Instantiate a fresh scenario from serializable definitions."""
    from simulation.entities import Car, Pedestrian

    scenario_rng = rng or random.Random()
    if name == RANDOM_SCENARIO_NAME:
        definition = generate_random_scenario_definition(
            world_width,
            rng=scenario_rng,
            moved_probability=moved_probability,
        )
    else:
        catalog = definitions or DEFAULT_SCENARIO_DEFINITIONS
        if name not in catalog:
            raise ValueError(f"Unknown scenario: {name}")
        definition = catalog[name]
    cars = [
        Car(
            x=float(car["x"]),
            y=road_y + float(car["y_offset"]),
            speed=float(car.get("speed", DEFAULT_VEHICLE_SPEED_KMH)),
            lane_index=1 if float(car["y_offset"]) >= 0 else 0,
        )
        for car in definition["cars"]
    ]
    pedestrians = [
        Pedestrian(
            x=float(person["x"]),
            y=road_y + float(person["y_offset"]),
            model=person.get("model", "man"),
            label=person.get("label"),
            action=person.get("action", "still"),
            speed=float(person.get("speed", DEFAULT_PEDESTRIAN_SPEED)),
            _rng=scenario_rng,
        )
        for person in definition["pedestrians"]
    ]
    return Scenario(cars=cars, pedestrians=pedestrians)
