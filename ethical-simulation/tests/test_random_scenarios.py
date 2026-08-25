from __future__ import annotations

import random
import unittest
from typing import get_args

from scenarios import (
    MOVING_PEDESTRIAN_ACTIONS,
    PEDESTRIAN_MODEL_CYCLE,
    PEDESTRIAN_MODELS,
    RANDOM_SCENARIO_NAME,
    generate_random_scenario_definition,
    validate_scenario_definitions,
)
from simulation.entities import PedestrianModel
from simulation.world import World


class RandomScenarioTests(unittest.TestCase):
    def test_runtime_models_derive_from_the_entity_type(self) -> None:
        self.assertEqual(set(get_args(PedestrianModel)), set(PEDESTRIAN_MODELS))
        self.assertNotIn("custom", PEDESTRIAN_MODEL_CYCLE)

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
            min_entities=7,
            max_entities=7,
            moved_probability=0.0,
        )
        second = generate_random_scenario_definition(
            1200,
            rng=random.Random(42),
            min_entities=7,
            max_entities=7,
            moved_probability=0.0,
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

    def test_moved_probability_controls_generated_actions(self) -> None:
        stationary = generate_random_scenario_definition(
            800,
            rng=random.Random(7),
            min_entities=10,
            max_entities=10,
            moved_probability=0.0,
        )
        moving = generate_random_scenario_definition(
            800,
            rng=random.Random(7),
            min_entities=10,
            max_entities=10,
            moved_probability=1.0,
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
        first = World(
            1200,
            800,
            RANDOM_SCENARIO_NAME,
            {},
            random_seed=99,
            moved_probability=0.1,
            rendering_enabled=False,
        )
        second = World(
            1200,
            800,
            RANDOM_SCENARIO_NAME,
            {},
            random_seed=99,
            moved_probability=0.1,
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
