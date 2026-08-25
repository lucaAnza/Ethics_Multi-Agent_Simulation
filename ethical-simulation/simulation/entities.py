"""Small, rendering-independent entity models."""

import math
import random
from dataclasses import dataclass, field
from typing import Literal, cast, get_args

from .units import vehicle_kmh_to_pixels_per_second


PedestrianModel = Literal[
    "man",
    "woman",
    "old_man",
    "old_woman",
    "boy",
    "girl",
    "custom",
]

# Runtime validation and random generation derive from the same typed source.
_PEDESTRIAN_MODEL_VALUES = cast(
    tuple[PedestrianModel, ...],
    get_args(PedestrianModel),
)
PEDESTRIAN_MODELS = frozenset(_PEDESTRIAN_MODEL_VALUES)
PEDESTRIAN_MODEL_CYCLE = tuple(
    model for model in _PEDESTRIAN_MODEL_VALUES if model != "custom"
)

PedestrianAction = Literal[
    "still",
    "move_right",
    "move_left",
    "move_down",
    "move_up",
    "random_move",
]

PEDESTRIAN_ACTIONS = frozenset(
    cast(tuple[PedestrianAction, ...], get_args(PedestrianAction))
)
MOVING_PEDESTRIAN_ACTIONS = tuple(
    sorted(action for action in PEDESTRIAN_ACTIONS if action != "still")
)


@dataclass
class Car:
    x: float
    y: float
    # Public vehicle speed is always expressed in km/h.
    speed: float = 50.0
    lane_index: int = 0
    _lane_change_start_y: float = field(default=0.0, init=False, repr=False)
    _lane_change_target_y: float = field(default=0.0, init=False, repr=False)
    _lane_change_target_index: int | None = field(default=None, init=False, repr=False)
    _lane_change_elapsed: float = field(default=0.0, init=False, repr=False)
    _lane_change_duration: float = field(default=0.10, init=False, repr=False)

    @property
    def is_changing_lane(self) -> bool:
        return self._lane_change_target_index is not None

    def start_lane_change(
        self,
        target_lane_index: int,
        target_y: float,
        duration: float = 0.10,
    ) -> bool:
        """Begin a linear vertical transition without changing vehicle heading."""
        if self.is_changing_lane or target_lane_index == self.lane_index:
            return False
        self._lane_change_start_y = self.y
        self._lane_change_target_y = target_y
        self._lane_change_target_index = target_lane_index
        self._lane_change_elapsed = 0.0
        self._lane_change_duration = max(0.001, duration)
        return True

    def update(self, delta_time: float) -> None:
        self.x += vehicle_kmh_to_pixels_per_second(self.speed) * delta_time
        if not self.is_changing_lane:
            return

        self._lane_change_elapsed += delta_time
        progress = min(1.0, self._lane_change_elapsed / self._lane_change_duration)
        self.y = self._lane_change_start_y + (
            self._lane_change_target_y - self._lane_change_start_y
        ) * progress
        if progress >= 1.0:
            self.y = self._lane_change_target_y
            self.lane_index = int(self._lane_change_target_index)
            self._lane_change_target_index = None

    def shift_lane_change_y(self, offset: float) -> None:
        """Keep an in-progress transition aligned after a window resize."""
        if self.is_changing_lane:
            self._lane_change_start_y += offset
            self._lane_change_target_y += offset


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
    _rng: random.Random = field(
        default_factory=random.Random,
        repr=False,
        compare=False,
    )

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
        self._random_heading = self._rng.uniform(0.0, 360.0)
        self._random_time_remaining = self._rng.uniform(0.65, 1.6)
