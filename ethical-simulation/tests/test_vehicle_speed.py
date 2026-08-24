from __future__ import annotations

import unittest

from simulation.entities import Car
from simulation.units import vehicle_kmh_to_pixels_per_second


class VehicleSpeedTests(unittest.TestCase):
    def test_50_kmh_preserves_the_established_visual_pace(self) -> None:
        self.assertEqual(120.0, vehicle_kmh_to_pixels_per_second(50.0))
        car = Car(x=0.0, y=0.0, speed=50.0)
        car.update(1.0)
        self.assertEqual(120.0, car.x)

    def test_car_speed_remains_expressed_in_kmh(self) -> None:
        car = Car(x=0.0, y=0.0, speed=37.5)
        car.update(0.5)
        self.assertEqual(37.5, car.speed)


if __name__ == "__main__":
    unittest.main()
