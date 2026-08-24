"""Persistent scenario definitions and factories for simulation state."""

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

if TYPE_CHECKING:
    from simulation.entities import Car, Pedestrian


SCENARIO_SETTINGS_PATH = Path(__file__).with_name("scenario_settings.json")
PEDESTRIAN_MODELS = {
    "man",
    "woman",
    "old_man",
    "old_woman",
    "boy",
    "girl",
    "custom",
}
PEDESTRIAN_ACTIONS = {
    "still",
    "move_right",
    "move_left",
    "move_down",
    "move_up",
    "random_move",
}

DEFAULT_SCENARIO_DEFINITIONS: dict[str, dict[str, list[dict[str, Any]]]] = {
    "Scenario 1": {
        "cars": [
            {"x": 130.0, "y_offset": -45.0, "speed": 50.0}
        ],
        "pedestrians": [
            {
                "x": 720.0,
                "y_offset": -25.0,
                "model": "man",
                "label": None,
                "action": "still",
                "speed": 55.0,
            }
        ],
    },
    "Scenario 2": {
        "cars": [
            {"x": 130.0, "y_offset": -45.0, "speed": 50.0}
        ],
        "pedestrians": [
            {"x": 400.0, "y_offset": 46.0, "model": "man", "label": None},
            {"x": 475.0, "y_offset": 46.0, "model": "woman", "label": None},
            {"x": 550.0, "y_offset": 46.0, "model": "old_man", "label": None},
            {"x": 625.0, "y_offset": 46.0, "model": "old_woman", "label": None},
            {"x": 700.0, "y_offset": 46.0, "model": "boy", "label": None},
            {"x": 775.0, "y_offset": 46.0, "model": "girl", "label": None},
            {"x": 760.0, "y_offset": -25.0, "model": "custom", "label": "Alex"},
        ],
    },
}


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
        if raw_name.strip() == "Scenario Free":
            continue
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
            speed = _finite_number(raw_car.get("speed", 50.0), "speed")
            if speed < 0:
                raise ValueError("car speed cannot be negative")
            cars.append(
                {
                    "x": _finite_number(raw_car.get("x"), "x"),
                    "y_offset": (
                        45.0
                        if _finite_number(raw_car.get("y_offset"), "y_offset") >= 0
                        else -45.0
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
            speed = _finite_number(raw_person.get("speed", 55.0), "speed")
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


def create_scenario(
    name: str,
    road_y: float,
    definitions: Mapping[str, Mapping[str, list[dict[str, Any]]]] | None = None,
    *,
    rng: random.Random | None = None,
) -> Scenario:
    """Instantiate a fresh scenario from serializable definitions."""
    from simulation.entities import Car, Pedestrian

    catalog = definitions or DEFAULT_SCENARIO_DEFINITIONS
    if name not in catalog:
        raise ValueError(f"Unknown scenario: {name}")
    definition = catalog[name]
    cars = [
        Car(
            x=float(car["x"]),
            y=road_y + float(car["y_offset"]),
            speed=float(car.get("speed", 50.0)),
            lane_index=1 if float(car["y_offset"]) >= 0 else 0,
        )
        for car in definition["cars"]
    ]
    scenario_rng = rng or random.Random()
    pedestrians = [
        Pedestrian(
            x=float(person["x"]),
            y=road_y + float(person["y_offset"]),
            model=person.get("model", "man"),
            label=person.get("label"),
            action=person.get("action", "still"),
            speed=float(person.get("speed", 55.0)),
            _rng=scenario_rng,
        )
        for person in definition["pedestrians"]
    ]
    return Scenario(cars=cars, pedestrians=pedestrians)
