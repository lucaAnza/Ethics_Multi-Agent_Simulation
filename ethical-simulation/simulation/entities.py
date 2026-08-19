"""Small, rendering-independent entity models."""

import math
from dataclasses import dataclass
from typing import Literal


PedestrianModel = Literal[
    "man",
    "woman",
    "old_man",
    "old_woman",
    "boy",
    "girl",
    "custom",
]


@dataclass
class Car:
    x: float
    y: float
    speed: float = 120.0
    direction: float = 1.0
    heading: float = 0.0
    steering_percent: float = 0.0
    brake_active: bool = False

    def update(self, delta_time: float) -> None:
        self.x += self.speed * self.direction * delta_time

    def update_driving(
        self,
        delta_time: float,
        throttle: bool,
        brake: bool,
        steering: float,
    ) -> None:
        """Apply simple arcade-style driving controls without realistic physics."""
        max_forward_speed = 260.0
        acceleration = 145.0
        braking = 260.0
        rolling_resistance = 65.0

        self.brake_active = brake
        self.steering_percent = max(-1.0, min(1.0, steering)) * 100.0

        if brake:
            self.speed = max(0.0, self.speed - braking * delta_time)
        elif throttle:
            self.speed = min(max_forward_speed, self.speed + acceleration * delta_time)
        elif self.speed > 0:
            self.speed = max(0.0, self.speed - rolling_resistance * delta_time)
        elif self.speed < 0:
            self.speed = min(0.0, self.speed + rolling_resistance * delta_time)

        if abs(self.speed) > 1.0:
            reverse_direction = -1.0 if self.speed < 0 else 1.0
            self.heading += steering * 105.0 * reverse_direction * delta_time

        heading_radians = math.radians(self.heading)
        self.x += math.cos(heading_radians) * self.speed * delta_time
        self.y += math.sin(heading_radians) * self.speed * delta_time


@dataclass
class Pedestrian:
    x: float
    y: float
    model: PedestrianModel = "man"
    label: str | None = None
    alive: bool = True
