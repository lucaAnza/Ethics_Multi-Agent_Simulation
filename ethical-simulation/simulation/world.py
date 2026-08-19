"""World state, stepping, reset, and prototype rendering."""

import math
from dataclasses import replace

import arcade

from scenarios import create_scenario
from simulation.entities import Car, Pedestrian


class World:
    """Own simulation state; only ``draw`` depends on Arcade rendering."""

    def __init__(self, width: int, height: int, scenario: str = "Scenario 1") -> None:
        self.width = width
        self.height = height
        self.scenario_name = scenario
        self.cars: list[Car] = []
        self.pedestrians: list[Pedestrian] = []
        self._label_texts: dict[int, arcade.Text] = {}
        self.reset(scenario)

    @property
    def road_y(self) -> float:
        return max(190.0, (self.height - 72) * 0.48)

    def update(self, delta_time: float) -> bool:
        """Advance automatic cars and report whether one touched a boundary."""
        boundary_hit = False
        for car in self.cars:
            car.update(delta_time)
            self._check_pedestrian_collisions(car)
            boundary_hit = self._keep_car_in_world(car) or boundary_hit
        return boundary_hit

    def update_free_drive(
        self,
        delta_time: float,
        throttle: bool,
        brake: bool,
        steering: float,
    ) -> bool:
        """Update the player-controlled car in Scenario Free."""
        if not self.cars:
            return False

        car = self.cars[0]
        car.update_driving(delta_time, throttle, brake, steering)
        boundary_hit = self._keep_car_in_world(car)
        self._check_pedestrian_collisions(car)
        return boundary_hit

    def stop_free_drive_controls(self) -> None:
        if self.cars:
            self.cars[0].brake_active = False
            self.cars[0].steering_percent = 0.0

    def _keep_car_in_world(self, car: Car) -> bool:
        playable_top = self.height - 72 - 24
        bounded_x = min(max(car.x, 40.0), self.width - 40.0)
        bounded_y = min(max(car.y, 30.0), playable_top)
        boundary_hit = (
            car.x <= 40.0
            or car.x >= self.width - 40.0
            or car.y <= 30.0
            or car.y >= playable_top
        )
        if boundary_hit:
            car.speed = 0.0
        car.x, car.y = bounded_x, bounded_y
        return boundary_hit

    def _check_pedestrian_collisions(self, car: Car) -> None:
        """Mark every living pedestrian touched by the car as dead."""
        for pedestrian in self.pedestrians:
            if pedestrian.alive and self._car_overlaps_pedestrian(car, pedestrian):
                pedestrian.alive = False

    @staticmethod
    def _car_overlaps_pedestrian(car: Car, pedestrian: Pedestrian) -> bool:
        heading = math.radians(car.heading)
        forward_x, forward_y = math.cos(heading), math.sin(heading)
        side_x, side_y = -forward_y, forward_x
        relative_x = pedestrian.x - car.x
        relative_y = pedestrian.y - car.y
        longitudinal = relative_x * forward_x + relative_y * forward_y
        lateral = relative_x * side_x + relative_y * side_y
        return abs(longitudinal) <= 48 and abs(lateral) <= 30

    def predict_action_outcomes(
        self,
        seconds: float = 2.0,
        time_step: float = 0.05,
    ) -> dict[str, list[Pedestrian]]:
        """Simulate three emergency actions without changing the real world."""
        if not self.cars:
            return {}

        _stop_time, stop_distance = self.braking_metrics()
        outcomes: dict[str, list[Pedestrian]] = {
            "Brake only": self._casualties_in_straight_corridor(stop_distance)
        }
        steps = max(1, math.ceil(seconds / time_step))

        for action_name, steering in (
            ("Maximum right steer", 1.0),
            ("Maximum left steer", -1.0),
        ):
            simulated_car = replace(self.cars[0])
            casualties: list[Pedestrian] = []
            casualty_ids: set[int] = set()

            for _ in range(steps):
                self._advance_prediction_car(simulated_car, time_step, steering)
                self._keep_car_in_world(simulated_car)
                for pedestrian in self.pedestrians:
                    if (
                        pedestrian.alive
                        and id(pedestrian) not in casualty_ids
                        and self._car_overlaps_pedestrian(simulated_car, pedestrian)
                    ):
                        casualties.append(pedestrian)
                        casualty_ids.add(id(pedestrian))

            outcomes[action_name] = casualties

        return outcomes

    def braking_metrics(self, braking_deceleration: float = 260.0) -> tuple[float, float]:
        """Return stopping time and distance for the current car."""
        if not self.cars:
            return 0.0, 0.0
        speed = abs(self.cars[0].speed * self.cars[0].direction)
        stop_time = speed / braking_deceleration
        stop_distance = speed * stop_time - 0.5 * braking_deceleration * stop_time**2
        return stop_time, stop_distance

    def _casualties_in_straight_corridor(self, distance: float) -> list[Pedestrian]:
        if not self.cars or distance <= 0:
            return []
        car = self.cars[0]
        return [
            pedestrian
            for pedestrian in self.pedestrians
            if pedestrian.alive
            and self._pedestrian_in_projected_corridor(car, pedestrian, distance)
        ]

    @staticmethod
    def _advance_prediction_car(
        car: Car,
        delta_time: float,
        steering: float,
    ) -> None:
        """Advance a cloned car with constant speed and hypothetical steering."""
        if abs(car.speed) > 1.0:
            reverse_direction = -1.0 if car.speed < 0 else 1.0
            car.heading += steering * 105.0 * reverse_direction * delta_time

        heading = math.radians(car.heading)
        car.x += math.cos(heading) * car.speed * car.direction * delta_time
        car.y += math.sin(heading) * car.speed * car.direction * delta_time

    def has_imminent_collision(self, seconds: float = 2.0) -> bool:
        """Return whether the current trajectory reaches a pedestrian soon."""
        return any(
            self._car_will_hit_pedestrian(car, pedestrian, seconds)
            for car in self.cars
            for pedestrian in self.pedestrians
            if pedestrian.alive
        )

    def predict_current_course_casualties(
        self,
        seconds: float = 2.0,
    ) -> list[Pedestrian]:
        """List living pedestrians hit if speed and heading remain unchanged."""
        if not self.cars:
            return []
        travel_distance = abs(self.cars[0].speed * self.cars[0].direction) * seconds
        return self._casualties_in_straight_corridor(travel_distance)

    @staticmethod
    def _car_will_hit_pedestrian(
        car: Car,
        pedestrian: Pedestrian,
        seconds: float,
    ) -> bool:
        travel_distance = abs(car.speed * car.direction) * seconds
        return World._pedestrian_in_projected_corridor(car, pedestrian, travel_distance)

    @staticmethod
    def _pedestrian_in_projected_corridor(
        car: Car,
        pedestrian: Pedestrian,
        travel_distance: float,
    ) -> bool:
        if travel_distance <= 0:
            return False

        movement_speed = car.speed * car.direction
        heading = math.radians(car.heading)
        if movement_speed < 0:
            heading += math.pi
        forward_x, forward_y = math.cos(heading), math.sin(heading)
        side_x, side_y = -forward_y, forward_x

        front_x = car.x + forward_x * 38
        front_y = car.y + forward_y * 38
        relative_x = pedestrian.x - front_x
        relative_y = pedestrian.y - front_y
        longitudinal = relative_x * forward_x + relative_y * forward_y
        lateral = relative_x * side_x + relative_y * side_y

        pedestrian_radius = 10
        corridor_half_width = 20 + pedestrian_radius
        return (
            -pedestrian_radius <= longitudinal <= travel_distance + pedestrian_radius
            and abs(lateral) <= corridor_half_width
        )

    def reset(self, scenario: str | None = None) -> None:
        if scenario is not None:
            self.scenario_name = scenario
        initial = create_scenario(self.scenario_name, self.road_y)
        self.cars = initial.cars
        self.pedestrians = initial.pedestrians
        self._label_texts.clear()

    def resize(self, width: int, height: int) -> None:
        old_road_y = self.road_y
        self.width, self.height = width, height
        shift = self.road_y - old_road_y
        for entity in [*self.cars, *self.pedestrians]:
            entity.y += shift

    def draw(self) -> None:
        arcade.draw_lbwh_rectangle_filled(0, 0, self.width, self.height, (91, 145, 79))

        road_bottom = self.road_y - 90
        arcade.draw_lbwh_rectangle_filled(0, road_bottom, self.width, 180, (55, 58, 62))
        arcade.draw_line(0, road_bottom + 10, self.width, road_bottom + 10, (235, 235, 220), 4)
        arcade.draw_line(0, road_bottom + 170, self.width, road_bottom + 170, (235, 235, 220), 4)
        for x in range(-20, self.width + 80, 110):
            arcade.draw_lbwh_rectangle_filled(x, self.road_y - 3, 65, 6, (245, 205, 65))

        self._draw_environment()
        for car in self.cars:
            self._draw_trajectory(car)
        for car in self.cars:
            self._draw_car(car)
        for pedestrian in self.pedestrians:
            self._draw_pedestrian(pedestrian)

    def _draw_environment(self) -> None:
        for x in (95, 280, self.width - 105):
            arcade.draw_lbwh_rectangle_filled(x - 7, self.road_y + 135, 14, 35, (105, 72, 45))
            arcade.draw_circle_filled(x, self.road_y + 180, 31, (31, 105, 50))
        arcade.draw_lbwh_rectangle_filled(390, self.road_y + 115, 150, 105, (194, 154, 112))
        arcade.draw_lbwh_rectangle_filled(415, self.road_y + 145, 30, 40, (90, 145, 183))
        arcade.draw_lbwh_rectangle_filled(475, self.road_y + 145, 30, 40, (90, 145, 183))

    def _draw_trajectory(self, car: Car, seconds: float = 2.0) -> None:
        """Draw the two dashed boundaries of the car's projected path."""
        movement_speed = car.speed * car.direction
        heading = math.radians(car.heading)
        if movement_speed < 0:
            heading += math.pi

        forward_x, forward_y = math.cos(heading), math.sin(heading)
        side_x, side_y = -forward_y, forward_x
        start_x = car.x + forward_x * 42
        start_y = car.y + forward_y * 42
        projected_length = abs(movement_speed) * seconds
        visible_length = max(55.0, projected_length)
        danger = self.has_imminent_collision(seconds)
        color = (245, 75, 75, 220) if danger else (80, 210, 245, 190)

        dash_length = 18.0
        dash_stride = 30.0
        for side in (-22.0, 22.0):
            offset_x, offset_y = side_x * side, side_y * side
            distance = 0.0
            while distance < visible_length:
                dash_end = min(distance + dash_length, visible_length)
                arcade.draw_line(
                    start_x + offset_x + forward_x * distance,
                    start_y + offset_y + forward_y * distance,
                    start_x + offset_x + forward_x * dash_end,
                    start_y + offset_y + forward_y * dash_end,
                    color,
                    2,
                )
                distance += dash_stride

    @staticmethod
    def _draw_car(car: Car) -> None:
        angle = math.radians(car.heading)
        cosine, sine = math.cos(angle), math.sin(angle)

        def rotated(local_x: float, local_y: float) -> tuple[float, float]:
            return (
                car.x + local_x * cosine - local_y * sine,
                car.y + local_x * sine + local_y * cosine,
            )

        body = [rotated(-38, -20), rotated(38, -20), rotated(38, 20), rotated(-38, 20)]
        windshield = [rotated(3, -15), rotated(22, -12), rotated(22, 12), rotated(3, 15)]
        arcade.draw_polygon_filled(body, (195, 45, 48))
        arcade.draw_polygon_filled(windshield, (155, 210, 225))
        arcade.draw_circle_filled(*rotated(31, -11), 4, (255, 240, 155))
        arcade.draw_circle_filled(*rotated(31, 11), 4, (255, 240, 155))

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
        arcade.draw_line(person.x, person.y - 15 * scale, person.x - 9 * scale, person.y - 31 * scale, leg_color, 4)
        arcade.draw_line(person.x, person.y - 15 * scale, person.x + 9 * scale, person.y - 31 * scale, leg_color, 4)

        if is_old:
            cane_x = person.x + 14
            arcade.draw_line(cane_x, person.y + 1, cane_x, person.y - 29, (110, 70, 35), 3)
            arcade.draw_line(cane_x, person.y + 1, cane_x - 5, person.y + 5, (110, 70, 35), 3)

        self._draw_pedestrian_label(person, person.y + (38 if is_child else 44))

    def _draw_dead_pedestrian(self, person: Pedestrian) -> None:
        """Draw a high-contrast white body and skull for a dead pedestrian."""
        white = (250, 250, 250)
        skull_x = person.x + 25
        arcade.draw_line(person.x - 18, person.y, person.x + 15, person.y, white, 9)
        arcade.draw_line(person.x - 8, person.y, person.x - 19, person.y - 10, white, 5)
        arcade.draw_line(person.x + 5, person.y, person.x + 15, person.y - 11, white, 5)
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
        arcade.draw_line(skull_x - 5, person.y - 7, skull_x + 5, person.y - 7, (25, 25, 28), 1)
        self._draw_pedestrian_label(person, person.y + 22)

    def _draw_pedestrian_label(self, person: Pedestrian, y: float) -> None:
        if person.label:
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
