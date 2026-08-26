from __future__ import annotations

import random
import tempfile
import unittest
from pathlib import Path
from typing import get_args

from scenarios import (
    DEFAULT_SCENARIO_DEFINITIONS,
    MOVING_PEDESTRIAN_ACTIONS,
    PEDESTRIAN_MODEL_CYCLE,
    PEDESTRIAN_MODELS,
    RANDOM_SCENARIO_NAME,
    RandomScenarioSettings,
    generate_random_scenario_definition,
    load_scenario_settings,
    save_scenario_settings,
    validate_scenario_definitions,
)
from simulation.entities import PedestrianModel
from simulation.world import World


class RandomScenarioTests(unittest.TestCase):
    def test_random_settings_validate_fixed_and_random_values(self) -> None:
        settings = RandomScenarioSettings.from_mapping(
            {
                "min_entities": 3,
                "max_entities": 8,
                "initial_speed": 65,
                "vision_distance": "random",
                "max_shifts": "random",
                "crazy_driver_probability": 0.25,
                "pedestrian_movement_probability": 0.4,
            }
        )
        self.assertIsNone(settings.vision_distance)
        self.assertIsNone(settings.max_shifts)
        self.assertEqual("random", settings.to_dict()["vision_distance"])
        self.assertEqual("random", settings.to_dict()["max_shifts"])

        with self.assertRaises(ValueError):
            RandomScenarioSettings.from_mapping(
                {"min_entities": 4, "max_entities": 3}
            )
        with self.assertRaises(ValueError):
            RandomScenarioSettings.from_mapping({"min_entities": 2.5})
        with self.assertRaises(ValueError):
            RandomScenarioSettings.from_mapping(
                {"pedestrian_movement_probability": 1.1}
            )
        with self.assertRaises(ValueError):
            RandomScenarioSettings.from_mapping(
                {"vision_distance": 150, "decision_distance": 200}
            )

    def test_random_settings_are_persisted_with_the_scenario_catalog(self) -> None:
        settings = RandomScenarioSettings(
            min_entities=4,
            max_entities=7,
            initial_speed=70,
            vision_distance=None,
            decision_distance=180,
            max_shifts=None,
            crazy_driver_probability=0.2,
            pedestrian_movement_probability=0.3,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scenario_settings.json"
            save_scenario_settings(DEFAULT_SCENARIO_DEFINITIONS, settings, path)
            loaded = load_scenario_settings(path)

        self.assertEqual(settings, loaded.random_scenario)
        self.assertEqual(
            set(DEFAULT_SCENARIO_DEFINITIONS),
            set(loaded.definitions),
        )

    def test_world_resolves_configured_random_vehicle_values_once_per_seed(
        self,
    ) -> None:
        settings = RandomScenarioSettings(
            min_entities=4,
            max_entities=4,
            initial_speed=50,
            vision_distance=None,
            decision_distance=210,
            max_shifts=None,
            crazy_driver_probability=1.0,
            pedestrian_movement_probability=1.0,
        )
        worlds = [
            World(
                1200,
                800,
                RANDOM_SCENARIO_NAME,
                {},
                random_seed=123,
                random_scenario_settings=settings,
                rendering_enabled=False,
            )
            for _index in range(2)
        ]
        first, second = worlds

        self.assertEqual(4, len(first.pedestrians))
        self.assertEqual(120.0, first.primary_car.speed)
        self.assertTrue(all(person.action != "still" for person in first.pedestrians))
        self.assertEqual(first.vision_distance, second.vision_distance)
        self.assertEqual(first.decision_distance, second.decision_distance)
        self.assertLessEqual(first.decision_distance, first.vision_distance)
        self.assertEqual(first.max_spostamenti, second.max_spostamenti)
        self.assertEqual(
            [(person.x, person.y, person.action) for person in first.pedestrians],
            [(person.x, person.y, person.action) for person in second.pedestrians],
        )

    def test_runtime_models_derive_from_the_entity_type(self) -> None:
        self.assertEqual(set(get_args(PedestrianModel)), set(PEDESTRIAN_MODELS))
        self.assertEqual(tuple(get_args(PedestrianModel)), PEDESTRIAN_MODEL_CYCLE)
        self.assertNotIn("custom", PEDESTRIAN_MODELS)

    def test_random_scenario_name_is_reserved_for_the_generator(self) -> None:
        with self.assertRaises(ValueError):
            validate_scenario_definitions(
                {
                    RANDOM_SCENARIO_NAME: {
                        "cars": [
                            {"x": 100.0, "y_offset": -45.0, "speed": 50.0}
                        ],
                        "pedestrians": [],
                    }
                }
            )

    def test_generation_is_reproducible_and_uses_both_lane_centers(self) -> None:
        first = generate_random_scenario_definition(
            1200,
            rng=random.Random(42),
            settings=RandomScenarioSettings(
                min_entities=7,
                max_entities=7,
                pedestrian_movement_probability=0.0,
            ),
        )
        second = generate_random_scenario_definition(
            1200,
            rng=random.Random(42),
            settings=RandomScenarioSettings(
                min_entities=7,
                max_entities=7,
                pedestrian_movement_probability=0.0,
            ),
        )

        self.assertEqual(first, second)
        pedestrians = first["pedestrians"]
        self.assertEqual(7, len(pedestrians))
        self.assertEqual(
            set(PEDESTRIAN_MODEL_CYCLE),
            {pedestrian["model"] for pedestrian in pedestrians},
        )
        self.assertTrue(
            all(person["y_offset"] in {-45.0, 45.0} for person in pedestrians)
        )
        self.assertTrue(
            all(320.0 <= person["x"] <= 1010.0 for person in pedestrians)
        )
        self.assertTrue(all(person["action"] == "still" for person in pedestrians))

    def test_movement_probability_controls_generated_actions(self) -> None:
        stationary = generate_random_scenario_definition(
            800,
            rng=random.Random(7),
            settings=RandomScenarioSettings(
                min_entities=10,
                max_entities=10,
                pedestrian_movement_probability=0.0,
            ),
        )
        moving = generate_random_scenario_definition(
            800,
            rng=random.Random(7),
            settings=RandomScenarioSettings(
                min_entities=10,
                max_entities=10,
                pedestrian_movement_probability=1.0,
            ),
        )

        self.assertTrue(
            all(person["action"] == "still" for person in stationary["pedestrians"])
        )
        self.assertTrue(
            all(
                person["action"] in MOVING_PEDESTRIAN_ACTIONS
                for person in moving["pedestrians"]
            )
        )

    def test_world_builds_identical_random_scenarios_from_the_same_seed(self) -> None:
        settings = RandomScenarioSettings(
            pedestrian_movement_probability=0.1,
        )
        first = World(
            1200,
            800,
            RANDOM_SCENARIO_NAME,
            {},
            random_seed=99,
            random_scenario_settings=settings,
            rendering_enabled=False,
        )
        second = World(
            1200,
            800,
            RANDOM_SCENARIO_NAME,
            {},
            random_seed=99,
            random_scenario_settings=settings,
            rendering_enabled=False,
        )
        snapshot = lambda world: [
            (
                person.x,
                person.y,
                person.model,
                person.label,
                person.action,
                person.speed,
            )
            for person in world.pedestrians
        ]

        self.assertEqual(snapshot(first), snapshot(second))


if __name__ == "__main__":
    unittest.main()
