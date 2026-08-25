from __future__ import annotations

import unittest

from decision_engine.modes import CODE_MODE, IMPLEMENTATION_MODES, LLM_MODE
from ethics.catalog import (
    FRAMEWORK_IMPLEMENTATIONS,
    FRAMEWORK_OPTIONS,
    FRAMEWORKS,
    LLM_FRAMEWORKS,
)
from llm.prompt_builder import PROMPT_FILENAMES
from scenarios import DEFAULT_SCENARIO_DEFINITIONS
from simulation.config import (
    CAR_HALF_LENGTH,
    DEFAULT_DECISION_DISTANCE,
    DEFAULT_MAX_LANE_CHANGES,
    DEFAULT_PEDESTRIAN_SPEED,
    DEFAULT_VEHICLE_SPEED_KMH,
    DEFAULT_VISION_DISTANCE,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    LANE_OFFSET,
)
from simulation.entities import (
    PEDESTRIAN_ACTION_LABELS,
    PEDESTRIAN_ACTIONS,
    PEDESTRIAN_CATEGORY_BY_MODEL,
    PEDESTRIAN_MODEL_LABELS,
    PEDESTRIAN_MODELS,
    Car,
    Pedestrian,
)
from simulation.world import World


class SharedConfigurationTests(unittest.TestCase):
    def test_entity_metadata_covers_the_typed_runtime_catalogs(self) -> None:
        self.assertEqual(PEDESTRIAN_MODELS, PEDESTRIAN_MODEL_LABELS.keys())
        self.assertEqual(PEDESTRIAN_MODELS, PEDESTRIAN_CATEGORY_BY_MODEL.keys())
        self.assertEqual(PEDESTRIAN_ACTIONS, PEDESTRIAN_ACTION_LABELS.keys())

    def test_framework_catalog_and_prompts_use_the_same_modes(self) -> None:
        self.assertEqual((CODE_MODE, LLM_MODE), IMPLEMENTATION_MODES)
        self.assertEqual(tuple(FRAMEWORK_IMPLEMENTATIONS), FRAMEWORKS)
        self.assertEqual(set(PROMPT_FILENAMES), set(LLM_FRAMEWORKS))
        self.assertEqual(
            {
                f"{name} ({implementation})"
                for name, implementations in FRAMEWORK_IMPLEMENTATIONS.items()
                for implementation in implementations
            },
            set(FRAMEWORK_OPTIONS),
        )

    def test_entity_and_world_defaults_come_from_simulation_config(self) -> None:
        self.assertEqual(DEFAULT_VEHICLE_SPEED_KMH, Car(0.0, 0.0).speed)
        self.assertEqual(DEFAULT_PEDESTRIAN_SPEED, Pedestrian(0.0, 0.0).speed)

        world = World(
            DEFAULT_WINDOW_WIDTH,
            DEFAULT_WINDOW_HEIGHT,
            "Scenario 1",
            DEFAULT_SCENARIO_DEFINITIONS,
            rendering_enabled=False,
        )
        self.assertEqual(DEFAULT_VISION_DISTANCE, world.vision_distance)
        self.assertEqual(DEFAULT_DECISION_DISTANCE, world.decision_distance)
        self.assertEqual(DEFAULT_MAX_LANE_CHANGES, world.max_spostamenti)
        self.assertEqual(LANE_OFFSET, world.LANE_OFFSET)
        self.assertEqual(CAR_HALF_LENGTH, world.CAR_HALF_LENGTH)


if __name__ == "__main__":
    unittest.main()
