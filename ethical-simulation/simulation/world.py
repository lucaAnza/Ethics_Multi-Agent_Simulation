"""Simulation state, vehicle perception, collisions, and map rendering."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable

import arcade

from scenarios import create_scenario
from simulation.entities import Car, Pedestrian


@dataclass(frozen=True)
class DecisionContext:
    """A single incident and the only state exposed to an ethical framework."""

    incident_entities: tuple[Pedestrian, ...]
    state: dict[str, list[dict[str, Any]]]


class World:
    """Own all physical and perceptual state independently from ethical policy."""

    ROAD_HALF_HEIGHT = 90.0
    LANE_OFFSET = 45.0
    LANE_HALF_WIDTH = 30.0
    CAR_HALF_LENGTH = 38.0
    CAR_HALF_WIDTH = 20.0
    LANE_CHANGE_DURATION = 0.10
    TUNNEL_MARGIN = 105.0

    def __init__(
        self,
        width: int,
        height: int,
        scenario: str = "Scenario 1",
        scenario_definitions: Mapping[
            str, Mapping[str, list[dict[str, Any]]]
        ] | None = None,
    ) -> None:
        self.width = width
        self.height = height
        self.scenario_name = scenario
        self.scenario_definitions = scenario_definitions
        self.cars: list[Car] = []
        self.pedestrians: list[Pedestrian] = []
        self.vision_distance = 300.0
        self.decision_distance = 120.0
        self.max_spostamenti = 2
        self.lane_changes_used = 0
        self.reached_tunnel = False
        self._handled_incident_ids: set[int] = set()
        self._label_texts: dict[int, arcade.Text] = {}
        self._tunnel_text = arcade.Text(
            "TUNNEL",
            0,
            0,
            (225, 231, 236),
            10,
            anchor_x="center",
            anchor_y="center",
            bold=True,
        )
        self._other_lane_vision_text = arcade.Text(
            "ADJACENT LANE VISION",
            0,
            0,
            (255, 166, 77, 235),
            8,
            anchor_x="left",
            anchor_y="center",
            bold=True,
        )
        self.reset(scenario)

    @property
    def road_y(self) -> float:
        return max(190.0, (self.height - 72) * 0.48)

    @property
    def lane_centers(self) -> tuple[float, float]:
        return self.road_y - self.LANE_OFFSET, self.road_y + self.LANE_OFFSET

    @property
    def tunnel_x(self) -> float:
        return self.width - self.TUNNEL_MARGIN

    @property
    def primary_car(self) -> Car | None:
        return self.cars[0] if self.cars else None

    @property
    def lane_changes_remaining(self) -> int:
        return max(0, self.max_spostamenti - self.lane_changes_used)

    def configure_vehicle(
        self,
        *,
        vision_distance: float | None = None,
        decision_distance: float | None = None,
        max_spostamenti: int | None = None,
    ) -> None:
        """Update simulation-owned perception and lane-change limits."""
        if vision_distance is not None:
            self.vision_distance = max(50.0, float(vision_distance))
        if decision_distance is not None:
            self.decision_distance = max(10.0, float(decision_distance))
        self.decision_distance = min(self.decision_distance, self.vision_distance)
        if max_spostamenti is not None:
            self.max_spostamenti = max(
                self.lane_changes_used,
                0,
                int(max_spostamenti),
            )

    def update(self, delta_time: float) -> bool:
        """Advance the world and return true only when the primary car enters the tunnel."""
        if self.reached_tunnel:
            return True

        for car in self.cars:
            car.update(delta_time)
        for index, car in enumerate(self.cars):
            if car.x + self.CAR_HALF_LENGTH >= self.tunnel_x:
                car.x = self.tunnel_x - self.CAR_HALF_LENGTH
                car.speed = 0.0
                if index == 0:
                    self.reached_tunnel = True

        self._update_pedestrians(delta_time)
        for car in self.cars:
            self._check_pedestrian_collisions(car)
        return self.reached_tunnel

    def request_lane_change(self) -> bool:
        """Start the sole vehicle intervention if one is still available."""
        car = self.primary_car
        if (
            car is None
            or car.is_changing_lane
            or self.lane_changes_used >= self.max_spostamenti
            or self.reached_tunnel
        ):
            return False
        target_lane = 1 - car.lane_index
        if not car.start_lane_change(
            target_lane,
            self.lane_centers[target_lane],
            self.LANE_CHANGE_DURATION,
        ):
            return False
        self.lane_changes_used += 1
        return True

    def _update_pedestrians(self, delta_time: float) -> None:
        playable_top = self.height - 72 - 12
        for pedestrian in self.pedestrians:
            pedestrian.update(delta_time)
            bounded_x = min(max(pedestrian.x, 12.0), self.width - 12.0)
            bounded_y = min(max(pedestrian.y, 12.0), playable_top)
            touched_boundary = (
                bounded_x != pedestrian.x or bounded_y != pedestrian.y
            )
            pedestrian.x, pedestrian.y = bounded_x, bounded_y
            if touched_boundary and pedestrian.action == "random_move":
                pedestrian.redirect_random_movement()

    def _check_pedestrian_collisions(self, car: Car) -> None:
        for pedestrian in self.pedestrians:
            if pedestrian.alive and self._car_overlaps_pedestrian(car, pedestrian):
                pedestrian.alive = False

    @classmethod
    def _car_overlaps_pedestrian(cls, car: Car, pedestrian: Pedestrian) -> bool:
        return (
            abs(pedestrian.x - car.x) <= cls.CAR_HALF_LENGTH + 10.0
            and abs(pedestrian.y - car.y) <= cls.CAR_HALF_WIDTH + 10.0
        )

    def dead_pedestrians(self) -> list[Pedestrian]:
        return [pedestrian for pedestrian in self.pedestrians if not pedestrian.alive]

    def _lane_for_y(self, y: float) -> int | None:
        distances = [abs(y - center) for center in self.lane_centers]
        closest_lane = min(range(2), key=distances.__getitem__)
        return closest_lane if distances[closest_lane] <= self.LANE_HALF_WIDTH else None

    def _distance_ahead(self, pedestrian: Pedestrian) -> float:
        car = self.primary_car
        if car is None:
            return float("inf")
        return pedestrian.x - (car.x + self.CAR_HALF_LENGTH)

    def visible_lane_entities(self) -> tuple[list[Pedestrian], list[Pedestrian]]:
        """Return visible living pedestrians in current and adjacent lanes."""
        car = self.primary_car
        if car is None:
            return [], []
        by_lane: dict[int, list[Pedestrian]] = {0: [], 1: []}
        for pedestrian in self.pedestrians:
            distance = self._distance_ahead(pedestrian)
            lane = self._lane_for_y(pedestrian.y)
            if (
                pedestrian.alive
                and lane is not None
                and 0.0 <= distance <= self.vision_distance
            ):
                by_lane[lane].append(pedestrian)
        for entities in by_lane.values():
            entities.sort(key=self._distance_ahead)
        return by_lane[car.lane_index], by_lane[1 - car.lane_index]

    def next_incident_distance(self) -> float | None:
        current_entities, _other_entities = self.visible_lane_entities()
        if not current_entities:
            return None
        return self._distance_ahead(current_entities[0])

    @staticmethod
    def _serialize_entities(
        entities: list[Pedestrian],
        distance_getter: Callable[[Pedestrian], float],
    ) -> list[dict[str, Any]]:
        return [
            {
                "model": entity.model,
                "label": entity.label,
                "distance": round(max(0.0, distance_getter(entity)), 2),
            }
            for entity in entities
        ]

    def next_decision_context(self) -> DecisionContext | None:
        """Return an unhandled incident once it reaches decision distance."""
        car = self.primary_car
        if car is None or car.is_changing_lane or self.reached_tunnel:
            return None
        current_entities, other_entities = self.visible_lane_entities()
        triggering_entities = tuple(
            entity
            for entity in current_entities
            if self._distance_ahead(entity) <= self.decision_distance
            and id(entity) not in self._handled_incident_ids
        )
        if not triggering_entities:
            return None

        # Both lanes inside the decision zone belong to the same incident. This
        # prevents an immediate second decision about the same local situation
        # after the car has completed a lane change.
        incident_entities = tuple(
            entity
            for entity in (*current_entities, *other_entities)
            if self._distance_ahead(entity) <= self.decision_distance
        )
        return DecisionContext(
            incident_entities=incident_entities,
            state={
                "current_lane_entities": self._serialize_entities(
                    current_entities,
                    self._distance_ahead,
                ),
                "other_lane_entities": self._serialize_entities(
                    other_entities,
                    self._distance_ahead,
                ),
            },
        )

    def mark_decision_handled(self, context: DecisionContext) -> None:
        self._handled_incident_ids.update(id(entity) for entity in context.incident_entities)

    def reset(self, scenario: str | None = None) -> None:
        if scenario is not None:
            self.scenario_name = scenario
        initial = create_scenario(
            self.scenario_name,
            self.road_y,
            self.scenario_definitions,
        )
        self.cars = initial.cars
        self.pedestrians = initial.pedestrians
        for car in self.cars:
            car.lane_index = 1 if car.y >= self.road_y else 0
            car.y = self.lane_centers[car.lane_index]
        self.lane_changes_used = 0
        self.reached_tunnel = False
        self._handled_incident_ids.clear()
        self._label_texts.clear()

    def set_scenario_definitions(
        self,
        definitions: Mapping[str, Mapping[str, list[dict[str, Any]]]],
    ) -> None:
        self.scenario_definitions = definitions

    def resize(self, width: int, height: int) -> None:
        old_road_y = self.road_y
        self.width, self.height = width, height
        shift = self.road_y - old_road_y
        for pedestrian in self.pedestrians:
            pedestrian.y += shift
        for car in self.cars:
            car.y += shift
            car.shift_lane_change_y(shift)

    def draw(self, *, show_vehicle_vision: bool = True) -> None:
        arcade.draw_lbwh_rectangle_filled(
            0,
            0,
            self.width,
            self.height,
            (87, 143, 78),
        )
        road_bottom = self.road_y - self.ROAD_HALF_HEIGHT
        arcade.draw_lbwh_rectangle_filled(
            0,
            road_bottom,
            self.width,
            self.ROAD_HALF_HEIGHT * 2,
            (53, 57, 62),
        )
        arcade.draw_line(
            0,
            road_bottom + 10,
            self.width,
            road_bottom + 10,
            (235, 235, 220),
            4,
        )
        arcade.draw_line(
            0,
            road_bottom + self.ROAD_HALF_HEIGHT * 2 - 10,
            self.width,
            road_bottom + self.ROAD_HALF_HEIGHT * 2 - 10,
            (235, 235, 220),
            4,
        )
        for x in range(-20, int(self.tunnel_x) + 80, 110):
            arcade.draw_lbwh_rectangle_filled(
                x,
                self.road_y - 3,
                65,
                6,
                (245, 205, 65),
            )

        self._draw_environment()
        if show_vehicle_vision and self.primary_car is not None:
            self._draw_vehicle_vision(self.primary_car)
        for car in self.cars:
            self._draw_car(car)
        for pedestrian in self.pedestrians:
            self._draw_pedestrian(pedestrian)
        self._draw_tunnel()

    def _draw_environment(self) -> None:
        usable_right = max(200.0, self.tunnel_x - 55.0)
        tree_positions = (90.0, 285.0, 520.0, 755.0)
        for index, x in enumerate(tree_positions):
            if x >= usable_right:
                continue
            y = self.road_y + (150 if index % 2 == 0 else 185)
            arcade.draw_lbwh_rectangle_filled(x - 6, y - 35, 12, 38, (105, 72, 45))
            arcade.draw_circle_filled(x, y + 14, 27, (31, 103, 50))
            arcade.draw_circle_filled(x - 16, y + 5, 18, (39, 122, 57))
            arcade.draw_circle_filled(x + 16, y + 6, 19, (36, 116, 53))

        for x in range(55, int(usable_right), 115):
            lower_y = self.road_y - 135 - (x // 115 % 2) * 24
            arcade.draw_circle_filled(x, lower_y, 13, (38, 112, 52))
            arcade.draw_circle_filled(x + 12, lower_y + 2, 10, (45, 128, 60))
            flower_color = (245, 206, 66) if (x // 115) % 2 else (235, 105, 135)
            arcade.draw_circle_filled(x - 18, lower_y - 3, 3, flower_color)
            arcade.draw_circle_filled(x + 27, lower_y + 8, 3, flower_color)

        if 540 < usable_right:
            arcade.draw_lbwh_rectangle_filled(
                382,
                self.road_y + 118,
                148,
                96,
                (194, 154, 112),
            )
            arcade.draw_polygon_filled(
                [
                    (370, self.road_y + 214),
                    (456, self.road_y + 260),
                    (542, self.road_y + 214),
                ],
                (126, 70, 55),
            )
            for window_x in (408, 474):
                arcade.draw_lbwh_rectangle_filled(
                    window_x,
                    self.road_y + 150,
                    27,
                    36,
                    (91, 151, 190),
                )

    def _draw_tunnel(self) -> None:
        road_bottom = self.road_y - self.ROAD_HALF_HEIGHT
        facade_left = self.tunnel_x - 18
        arcade.draw_lbwh_rectangle_filled(
            facade_left,
            road_bottom - 24,
            self.width - facade_left,
            self.ROAD_HALF_HEIGHT * 2 + 48,
            (83, 88, 92),
        )
        for y in range(int(road_bottom - 18), int(road_bottom + 205), 28):
            arcade.draw_line(
                facade_left,
                y,
                self.width,
                y,
                (104, 109, 113),
                1,
            )
        arcade.draw_lbwh_rectangle_filled(
            self.tunnel_x + 6,
            road_bottom + 6,
            self.width - self.tunnel_x,
            self.ROAD_HALF_HEIGHT * 2 - 12,
            (15, 18, 22),
        )
        arcade.draw_lbwh_rectangle_filled(
            self.tunnel_x - 8,
            road_bottom - 6,
            14,
            self.ROAD_HALF_HEIGHT * 2 + 12,
            (132, 137, 140),
        )
        arcade.draw_line(
            self.tunnel_x - 1,
            road_bottom + 2,
            self.tunnel_x - 1,
            road_bottom + self.ROAD_HALF_HEIGHT * 2 - 2,
            (183, 188, 190),
            2,
        )
        self._tunnel_text.x = self.tunnel_x + 43
        self._tunnel_text.y = road_bottom + self.ROAD_HALF_HEIGHT * 2 + 11
        self._tunnel_text.draw()

    @staticmethod
    def _draw_dashed_horizontal(
        start_x: float,
        end_x: float,
        y: float,
        color,
        width: float = 2.0,
    ) -> None:
        x = start_x
        while x < end_x:
            arcade.draw_line(x, y, min(x + 18.0, end_x), y, color, width)
            x += 30.0

    @staticmethod
    def _draw_dashed_polyline(
        points: list[tuple[float, float]],
        color,
        width: float = 3.0,
        dash_length: float = 18.0,
        gap_length: float = 10.0,
    ) -> None:
        """Draw evenly spaced dashes across connected line segments."""
        if len(points) < 2:
            return

        drawing = True
        pattern_remaining = dash_length
        for start, end in zip(points, points[1:]):
            delta_x = end[0] - start[0]
            delta_y = end[1] - start[1]
            segment_length = (delta_x**2 + delta_y**2) ** 0.5
            if segment_length == 0:
                continue

            travelled = 0.0
            while travelled < segment_length:
                step = min(pattern_remaining, segment_length - travelled)
                start_ratio = travelled / segment_length
                end_ratio = (travelled + step) / segment_length
                if drawing:
                    arcade.draw_line(
                        start[0] + delta_x * start_ratio,
                        start[1] + delta_y * start_ratio,
                        start[0] + delta_x * end_ratio,
                        start[1] + delta_y * end_ratio,
                        color,
                        width,
                    )
                travelled += step
                pattern_remaining -= step
                if pattern_remaining <= 1e-6:
                    drawing = not drawing
                    pattern_remaining = dash_length if drawing else gap_length

    @staticmethod
    def _lane_vision_boundary(
        start_x: float,
        start_y: float,
        target_x: float,
        target_y: float,
        end_x: float,
    ) -> list[tuple[float, float]]:
        """Create a smooth sensor-to-lane boundary followed by a straight rail."""
        control_x = start_x + (target_x - start_x) * 0.7
        points: list[tuple[float, float]] = []
        for step in range(13):
            progress = step / 12
            inverse = 1.0 - progress
            points.append(
                (
                    inverse**2 * start_x
                    + 2 * inverse * progress * control_x
                    + progress**2 * target_x,
                    inverse**2 * start_y
                    + 2 * inverse * progress * target_y
                    + progress**2 * target_y,
                )
            )
        points.append((end_x, target_y))
        return points

    def _draw_vehicle_vision(self, car: Car) -> None:
        start_x = car.x + self.CAR_HALF_LENGTH + 4.0
        end_x = min(start_x + self.vision_distance, self.tunnel_x)
        if end_x <= start_x:
            return
        vision_color = (80, 210, 245, 205)
        for y in (car.y - self.LANE_HALF_WIDTH, car.y + self.LANE_HALF_WIDTH):
            self._draw_dashed_horizontal(start_x, end_x, y, vision_color)

        other_lane_y = self.lane_centers[1 - car.lane_index]
        transition_end_x = min(start_x + 58.0, end_x)
        other_lane_color = (255, 125, 18, 235)
        for target_y in (
            other_lane_y - self.LANE_HALF_WIDTH,
            other_lane_y + self.LANE_HALF_WIDTH,
        ):
            boundary = self._lane_vision_boundary(
                start_x,
                car.y,
                transition_end_x,
                target_y,
                end_x,
            )
            self._draw_dashed_polyline(
                boundary,
                other_lane_color,
                width=4.0,
                dash_length=18.0,
                gap_length=11.0,
            )

        label_x = min(transition_end_x + 10.0, end_x - 5.0)
        self._other_lane_vision_text.x = label_x
        self._other_lane_vision_text.y = other_lane_y
        self._other_lane_vision_text.draw()

    @staticmethod
    def _draw_car(car: Car) -> None:
        body = [
            (car.x - 38, car.y - 20),
            (car.x + 38, car.y - 20),
            (car.x + 38, car.y + 20),
            (car.x - 38, car.y + 20),
        ]
        windshield = [
            (car.x + 3, car.y - 15),
            (car.x + 22, car.y - 12),
            (car.x + 22, car.y + 12),
            (car.x + 3, car.y + 15),
        ]
        arcade.draw_polygon_filled(body, (195, 45, 48))
        arcade.draw_polygon_filled(windshield, (155, 210, 225))
        arcade.draw_circle_filled(car.x + 31, car.y - 11, 4, (255, 240, 155))
        arcade.draw_circle_filled(car.x + 31, car.y + 11, 4, (255, 240, 155))

    def _draw_pedestrian(self, person: Pedestrian) -> None:
        if not person.alive:
            self._draw_dead_pedestrian(person)
            return

        is_child = person.model in {"boy", "girl"}
        is_woman = person.model in {"woman", "old_woman", "girl"}
        is_old = person.model in {"old_man", "old_woman"}
        scale = 0.72 if is_child else 1.0
        skin = (235, 190, 145)
        clothes = {
            "man": (45, 80, 160),
            "woman": (175, 65, 125),
            "old_man": (100, 110, 125),
            "old_woman": (125, 85, 145),
            "boy": (45, 145, 190),
            "girl": (225, 105, 145),
            "custom": (245, 150, 40),
        }[person.model]

        head_y = person.y + 16 * scale
        arcade.draw_circle_filled(person.x, head_y, 9 * scale, skin)
        hair = (205, 205, 205) if is_old else (75, 48, 30)
        arcade.draw_line(
            person.x - 6 * scale,
            head_y + 5 * scale,
            person.x + 6 * scale,
            head_y + 5 * scale,
            hair,
            max(2, 4 * scale),
        )

        if is_woman:
            arcade.draw_triangle_filled(
                person.x,
                person.y + 7 * scale,
                person.x - 10 * scale,
                person.y - 17 * scale,
                person.x + 10 * scale,
                person.y - 17 * scale,
                clothes,
            )
        else:
            arcade.draw_line(
                person.x,
                person.y + 7 * scale,
                person.x,
                person.y - 17 * scale,
                clothes,
                max(5, 7 * scale),
            )

        leg_color = (35, 35, 40)
        arcade.draw_line(
            person.x,
            person.y - 15 * scale,
            person.x - 9 * scale,
            person.y - 31 * scale,
            leg_color,
            4,
        )
        arcade.draw_line(
            person.x,
            person.y - 15 * scale,
            person.x + 9 * scale,
            person.y - 31 * scale,
            leg_color,
            4,
        )

        if is_old:
            cane_x = person.x + 14
            arcade.draw_line(
                cane_x,
                person.y + 1,
                cane_x,
                person.y - 29,
                (110, 70, 35),
                3,
            )
            arcade.draw_line(
                cane_x,
                person.y + 1,
                cane_x - 5,
                person.y + 5,
                (110, 70, 35),
                3,
            )

        self._draw_pedestrian_label(person, person.y + (38 if is_child else 44))

    def _draw_dead_pedestrian(self, person: Pedestrian) -> None:
        white = (250, 250, 250)
        skull_x = person.x + 25
        arcade.draw_line(person.x - 18, person.y, person.x + 15, person.y, white, 9)
        arcade.draw_line(
            person.x - 8,
            person.y,
            person.x - 19,
            person.y - 10,
            white,
            5,
        )
        arcade.draw_line(
            person.x + 5,
            person.y,
            person.x + 15,
            person.y - 11,
            white,
            5,
        )
        arcade.draw_circle_filled(skull_x, person.y, 11, white)
        arcade.draw_lbwh_rectangle_filled(skull_x - 7, person.y - 10, 14, 8, white)
        arcade.draw_circle_filled(skull_x - 4, person.y + 2, 2.5, (25, 25, 28))
        arcade.draw_circle_filled(skull_x + 4, person.y + 2, 2.5, (25, 25, 28))
        arcade.draw_triangle_filled(
            skull_x,
            person.y - 1,
            skull_x - 2,
            person.y - 5,
            skull_x + 2,
            person.y - 5,
            (25, 25, 28),
        )
        arcade.draw_line(
            skull_x - 5,
            person.y - 7,
            skull_x + 5,
            person.y - 7,
            (25, 25, 28),
            1,
        )
        self._draw_pedestrian_label(person, person.y + 22)

    def _draw_pedestrian_label(self, person: Pedestrian, y: float) -> None:
        if not person.label:
            return
        cache_key = id(person)
        label = self._label_texts.get(cache_key)
        if label is None:
            label = arcade.Text(
                person.label,
                person.x,
                y,
                (255, 255, 255),
                9,
                anchor_x="center",
                anchor_y="bottom",
            )
            self._label_texts[cache_key] = label
        else:
            label.text = person.label
            label.x = person.x
            label.y = y
        label.draw()
