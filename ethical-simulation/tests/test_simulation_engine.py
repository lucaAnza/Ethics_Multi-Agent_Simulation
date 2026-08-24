from __future__ import annotations

import unittest

from ethics.utilitarian import DEFAULT_ENTITIES_VALUES, UtilitarianFramework
from simulation.engine import SimulationEngine
from simulation.world import World


SCENARIOS = {
    "Test": {
        "cars": [{"x": 100.0, "y_offset": -45.0, "speed": 50.0}],
        "pedestrians": [
            {
                "x": 400.0,
                "y_offset": -45.0,
                "model": "boy",
                "label": None,
                "action": "still",
                "speed": 0.0,
            },
            {
                "x": 400.0,
                "y_offset": 45.0,
                "model": "man",
                "label": None,
                "action": "still",
                "speed": 0.0,
            },
        ],
    }
}


class SharedSimulationEngineTests(unittest.TestCase):
    def test_headless_engine_runs_the_complete_deterministic_flow(self) -> None:
        world = World(
            700,
            600,
            "Test",
            SCENARIOS,
            random_seed=42,
            rendering_enabled=False,
        )
        world.configure_vehicle(
            vision_distance=300,
            decision_distance=120,
            max_spostamenti=2,
        )
        framework = UtilitarianFramework(DEFAULT_ENTITIES_VALUES)
        engine = SimulationEngine(
            world=world,
            framework_name="Utilitarianism",
            implementation="code",
            framework=framework,
            framework_settings_provider=lambda _name: {
                "entity_values": DEFAULT_ENTITIES_VALUES
            },
        )

        events = []
        for _step in range(1000):
            result = engine.step(1 / 60)
            if result.decision_event is not None:
                events.append(result.decision_event)
            if result.reached_tunnel:
                break

        self.assertTrue(engine.finished)
        self.assertEqual(1, len(events))
        self.assertEqual("CHANGE_LANE", events[0].applied_decision.action)
        self.assertEqual(1, world.lane_changes_used)
        self.assertEqual(1, len(framework.decision_history))
        self.assertEqual(1, len(world.dead_pedestrians()))

    def test_headless_world_rejects_accidental_drawing(self) -> None:
        world = World(
            700,
            600,
            "Test",
            SCENARIOS,
            rendering_enabled=False,
        )
        with self.assertRaises(RuntimeError):
            world.draw()


if __name__ == "__main__":
    unittest.main()
