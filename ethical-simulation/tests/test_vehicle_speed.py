from __future__ import annotations

import unittest

from scenarios.scenarios import validate_scenario_definitions
from simulation.entities import Car
from simulation.units import (
    VEHICLE_PIXELS_PER_SECOND_PER_KMH,
    vehicle_kmh_to_pixels_per_second,
)


class VehicleSpeedTests(unittest.TestCase):
    def test_car_movement_uses_the_centralized_conversion(self) -> None:
        expected_distance = 50.0 * VEHICLE_PIXELS_PER_SECOND_PER_KMH
        self.assertEqual(
            expected_distance,
            vehicle_kmh_to_pixels_per_second(50.0),
        )
        car = Car(x=0.0, y=0.0, speed=50.0)
        car.update(1.0)
        self.assertEqual(expected_distance, car.x)

    def test_car_speed_remains_expressed_in_kmh(self) -> None:
        car = Car(x=0.0, y=0.0, speed=37.5)
        car.update(0.5)
        self.assertEqual(37.5, car.speed)

    def test_scenario_accepts_a_stopped_car(self) -> None:
        scenarios = validate_scenario_definitions(
            {
                "Stopped": {
                    "cars": [
                        {
                            "x": 100.0,
                            "y_offset": -45.0,
                            "speed": 0.0,
                        }
                    ],
                    "pedestrians": [],
                }
            }
        )
        self.assertEqual(0.0, scenarios["Stopped"]["cars"][0]["speed"])


if __name__ == "__main__":
    unittest.main()
