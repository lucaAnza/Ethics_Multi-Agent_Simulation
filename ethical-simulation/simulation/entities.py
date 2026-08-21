"""Small, rendering-independent entity models."""

import math
import random
from dataclasses import dataclass, field
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

PedestrianAction = Literal[
    "still",
    "move_right",
    "move_left",
    "move_down",
    "move_up",
    "random_move",
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
        heading_radians = math.radians(self.heading)
        self.x += math.cos(heading_radians) * self.speed * self.direction * delta_time
        self.y += math.sin(heading_radians) * self.speed * self.direction * delta_time

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
            self.heading -= steering * 105.0 * reverse_direction * delta_time

        heading_radians = math.radians(self.heading)
        self.x += math.cos(heading_radians) * self.speed * delta_time
        self.y += math.sin(heading_radians) * self.speed * delta_time


@dataclass
class Pedestrian:
    x: float
    y: float
    model: PedestrianModel = "man"
    label: str | None = None
    action: PedestrianAction = "still"
    speed: float = 55.0
    alive: bool = True
    _random_heading: float = field(default=0.0, init=False, repr=False)
    _random_time_remaining: float = field(default=0.0, init=False, repr=False)

    def update(self, delta_time: float) -> None:
        """Advance the configured pedestrian action."""
        if not self.alive or self.action == "still" or self.speed <= 0:
            return

        directions = {
            "move_right": (1.0, 0.0),
            "move_left": (-1.0, 0.0),
            "move_down": (0.0, -1.0),
            "move_up": (0.0, 1.0),
        }
        if self.action == "random_move":
            self._random_time_remaining -= delta_time
            if self._random_time_remaining <= 0:
                self.redirect_random_movement()
            radians = math.radians(self._random_heading)
            direction_x, direction_y = math.cos(radians), math.sin(radians)
        else:
            direction_x, direction_y = directions.get(self.action, (0.0, 0.0))

        self.x += direction_x * self.speed * delta_time
        self.y += direction_y * self.speed * delta_time

    def redirect_random_movement(self) -> None:
        """Choose a new direction and hold it briefly for smooth random motion."""
        self._random_heading = random.uniform(0.0, 360.0)
        self._random_time_remaining = random.uniform(0.65, 1.6)
