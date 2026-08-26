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
from simulation.entity_factory import EntityFactory

if TYPE_CHECKING:
    from simulation.entities import Car, Pedestrian

from .config import (
    DEFAULT_CAR_START_X,
    DEFAULT_PEDESTRIAN_SPEED,
    DEFAULT_RANDOM_SCENARIO_SETTINGS,
    DEFAULT_SCENARIO_DEFINITIONS,
    DEFAULT_VEHICLE_SPEED_KMH,
    LANE_OFFSET,
    RANDOM_PEDESTRIAN_SPEED_RANGE,
    RANDOM_SCENARIO_END_MARGIN,
    RANDOM_SCENARIO_FIRST_ENTITY_X,
    RANDOM_SCENARIO_NAME,
    RANDOM_SCENARIO_POSITION_JITTER_RATIO,
    REMOVED_SCENARIO_NAMES,
    RandomScenarioSettings,
    ResolvedRandomScenarioSettings,
    SCENARIO_SETTINGS_PATH,
)


@dataclass
class Scenario:
    cars: list[Car]
    pedestrians: list[Pedestrian]
    random_settings: ResolvedRandomScenarioSettings | None = None


@dataclass(frozen=True)
class ScenarioSettings:
    """Validated persistent settings loaded as one coherent unit."""

    definitions: dict[str, dict[str, list[dict[str, Any]]]]
    random_scenario: RandomScenarioSettings


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


def validate_random_scenario_settings(
    settings: RandomScenarioSettings | Mapping[str, object] | None,
) -> RandomScenarioSettings:
    if isinstance(settings, RandomScenarioSettings):
        return settings
    return RandomScenarioSettings.from_mapping(settings)


def load_scenario_settings(
    path: Path = SCENARIO_SETTINGS_PATH,
) -> ScenarioSettings:
    """Load scenario entities and random-generator settings from one file."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("scenario settings must be a JSON object")
    except (OSError, json.JSONDecodeError, ValueError) as error:
        application_logger.log_message(
            f"[SCENARIO SETTINGS] Using defaults: {error}"
        )
        return ScenarioSettings(
            definitions=validate_scenario_definitions(
                deepcopy(DEFAULT_SCENARIO_DEFINITIONS)
            ),
            random_scenario=DEFAULT_RANDOM_SCENARIO_SETTINGS,
        )

    try:
        definitions = validate_scenario_definitions(payload.get("scenarios"))
    except ValueError as error:
        application_logger.log_message(
            f"[SCENARIO SETTINGS] Invalid scenario catalog; using defaults: {error}"
        )
        definitions = validate_scenario_definitions(
            deepcopy(DEFAULT_SCENARIO_DEFINITIONS)
        )

    try:
        random_settings = validate_random_scenario_settings(
            payload.get("random_scenario")
        )
    except ValueError as error:
        application_logger.log_message(
            "[SCENARIO SETTINGS] Invalid random scenario settings; "
            f"using defaults: {error}"
        )
        random_settings = DEFAULT_RANDOM_SCENARIO_SETTINGS
    return ScenarioSettings(definitions, random_settings)


def load_scenario_definitions(
    path: Path = SCENARIO_SETTINGS_PATH,
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Compatibility helper returning only the persistent entity catalog."""
    return load_scenario_settings(path).definitions


def save_scenario_settings(
    definitions: Mapping[str, Mapping[str, list[dict[str, Any]]]],
    random_settings: RandomScenarioSettings | Mapping[str, object],
    path: Path = SCENARIO_SETTINGS_PATH,
) -> ScenarioSettings:
    """Validate and atomically save all scenario settings."""
    normalized = validate_scenario_definitions(definitions)
    normalized_random = validate_random_scenario_settings(random_settings)
    payload = {
        "version": 3,
        "random_scenario": normalized_random.to_dict(),
        "scenarios": normalized,
    }
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)
    return ScenarioSettings(normalized, normalized_random)


def save_scenario_definitions(
    definitions: Mapping[str, Mapping[str, list[dict[str, Any]]]],
    path: Path = SCENARIO_SETTINGS_PATH,
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Compatibility helper preserving the current random settings."""
    saved = save_scenario_settings(
        definitions,
        load_scenario_settings(path).random_scenario,
        path,
    )
    return saved.definitions


def generate_random_scenario_definition(
    world_width: float,
    *,
    rng: random.Random,
    settings: RandomScenarioSettings | Mapping[str, object] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Generate one seeded two-lane scenario as a serializable definition."""
    normalized = validate_random_scenario_settings(settings)
    return _generate_random_definition(
        world_width,
        rng=rng,
        settings=normalized.resolve(rng),
    )


def _generate_random_definition(
    world_width: float,
    *,
    rng: random.Random,
    settings: ResolvedRandomScenarioSettings,
) -> dict[str, list[dict[str, Any]]]:
    """Generate entities from values already resolved for this seeded run."""
    entity_count = rng.randint(settings.min_entities, settings.max_entities)
    probability = settings.pedestrian_movement_probability
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
    for x, model in zip(positions, models):
        moves = rng.random() < probability
        action = rng.choice(MOVING_PEDESTRIAN_ACTIONS) if moves else "still"
        pedestrians.append(
            {
                "x": round(x, 2),
                "y_offset": rng.choice((-LANE_OFFSET, LANE_OFFSET)),
                "model": model,
                "label": None,
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
                "speed": settings.initial_speed,
            }
        ],
        "pedestrians": pedestrians,
    }


class ScenarioFactory:
    """Create fixed or generated scenarios through one construction path."""

    @staticmethod
    def create(
        name: str,
        road_y: float,
        definitions: (
            Mapping[str, Mapping[str, list[dict[str, Any]]]] | None
        ) = None,
        *,
        rng: random.Random | None = None,
        world_width: float = DEFAULT_WINDOW_WIDTH,
        random_settings: (
            RandomScenarioSettings | Mapping[str, object] | None
        ) = None,
    ) -> Scenario:
        """Instantiate a fresh scenario from serializable definitions."""
        scenario_rng = rng or random.Random()
        resolved_random_settings = None
        if name == RANDOM_SCENARIO_NAME:
            normalized_settings = validate_random_scenario_settings(
                random_settings
            )
            resolved_random_settings = normalized_settings.resolve(scenario_rng)
            definition = _generate_random_definition(
                world_width,
                rng=scenario_rng,
                settings=resolved_random_settings,
            )
        else:
            catalog = definitions or DEFAULT_SCENARIO_DEFINITIONS
            if name not in catalog:
                raise ValueError(f"Unknown scenario: {name}")
            definition = catalog[name]

        return Scenario(
            cars=[
                EntityFactory.create_car(car, road_y)
                for car in definition["cars"]
            ],
            pedestrians=[
                EntityFactory.create_pedestrian(
                    person,
                    road_y,
                    rng=scenario_rng,
                )
                for person in definition["pedestrians"]
            ],
            random_settings=resolved_random_settings,
        )


def create_scenario(
    name: str,
    road_y: float,
    definitions: Mapping[str, Mapping[str, list[dict[str, Any]]]] | None = None,
    *,
    rng: random.Random | None = None,
    world_width: float = DEFAULT_WINDOW_WIDTH,
    random_settings: RandomScenarioSettings | Mapping[str, object] | None = None,
) -> Scenario:
    """Compatibility wrapper around :class:`ScenarioFactory`."""
    return ScenarioFactory.create(
        name,
        road_y,
        definitions,
        rng=rng,
        world_width=world_width,
        random_settings=random_settings,
    )
