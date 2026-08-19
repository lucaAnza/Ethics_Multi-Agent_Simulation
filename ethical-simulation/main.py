"""Interactive entry point for Ethical Multi-Agent Simulation."""

import arcade
import arcade.gui

from simulation import World
from simulation.entities import Pedestrian

SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
TOOLBAR_HEIGHT = 72

FRAMEWORKS = ["Utilitarianism", "Kant", "Constant", "Ross", "Virtue Ethics"]
SCENARIOS = ["Scenario 1", "Scenario 2", "Scenario Free"]


class SimulationWindow(arcade.Window):
    def __init__(self) -> None:
        super().__init__(
            SCREEN_WIDTH,
            SCREEN_HEIGHT,
            "Ethical Multi-Agent Simulation",
            resizable=True,
        )
        self.set_minimum_size(1000, 500)
        self.current_framework = "Utilitarianism"
        self.current_scenario = "Scenario 1"
        self.is_running = False
        self.time_scale = 1.0
        self.pressed_keys: set[int] = set()
        self._last_debug_prediction: tuple[tuple[str, tuple[int, ...]], ...] | None = None

        self.world = World(self.width, self.height, self.current_scenario)
        self._hud_texts = self._create_hud_texts()
        self._prediction_texts = self._create_prediction_texts()
        self.manager = arcade.gui.UIManager()
        self._setup_toolbar()
        self.manager.enable()
        arcade.set_background_color((91, 145, 79))

    def _setup_toolbar(self) -> None:
        row = arcade.gui.UIBoxLayout(vertical=False, space_between=8)
        row.add(arcade.gui.UILabel(text="Framework", width=72))
        framework = row.add(
            arcade.gui.UIDropdown(
                default=self.current_framework, options=FRAMEWORKS, width=140, height=38
            )
        )
        row.add(arcade.gui.UILabel(text="Simulation", width=72))
        scenario = row.add(
            arcade.gui.UIDropdown(
                default=self.current_scenario, options=SCENARIOS, width=120, height=38
            )
        )

        self.time_scale_label = row.add(
            arcade.gui.UILabel(text="Time x1", width=72)
        )
        time_slider = row.add(
            arcade.gui.UISlider(
                value=self.time_scale,
                min_value=0.25,
                max_value=2.0,
                step=0.25,
                width=100,
                height=30,
            )
        )

        for label, handler, width in (
            ("Play", self._play, 58),
            ("Pause", self._pause, 62),
            ("Reset", self._reset, 62),
            ("Settings", self._settings, 78),
            ("Info", self._info, 52),
        ):
            button = row.add(arcade.gui.UIFlatButton(text=label, width=width, height=38))
            button.on_click = handler

        framework.on_change = self._framework_changed
        scenario.on_change = self._scenario_changed
        time_slider.on_change = self._time_scale_changed
        anchor = arcade.gui.UIAnchorLayout()
        anchor.add(row, anchor_x="left", anchor_y="top", align_x=18, align_y=-17)
        self.manager.add(anchor)

    def _framework_changed(self, event: arcade.gui.UIOnChangeEvent) -> None:
        if event.new_value is not None:
            self.current_framework = event.new_value

    def _scenario_changed(self, event: arcade.gui.UIOnChangeEvent) -> None:
        if event.new_value is not None:
            self.current_scenario = event.new_value
            self.pressed_keys.clear()
            self.world.reset(self.current_scenario)
            self._last_debug_prediction = None

    def _time_scale_changed(self, event: arcade.gui.UIOnChangeEvent) -> None:
        if event.new_value is not None:
            self.time_scale = float(event.new_value)
            self.time_scale_label.text = f"Time x{self.time_scale:g}"

    def _play(self, _event: arcade.gui.UIOnClickEvent) -> None:
        self.is_running = True

    def _pause(self, _event: arcade.gui.UIOnClickEvent) -> None:
        self.is_running = False
        self.world.stop_free_drive_controls()

    def _reset(self, _event: arcade.gui.UIOnClickEvent) -> None:
        self.pressed_keys.clear()
        self.world.reset()
        self._last_debug_prediction = None

    @staticmethod
    def _settings(_event: arcade.gui.UIOnClickEvent) -> None:
        print("Settings panel will be added in a future version.")

    @staticmethod
    def _info(_event: arcade.gui.UIOnClickEvent) -> None:
        print("Ethical Multi-Agent Simulation — prototype")

    def on_update(self, delta_time: float) -> None:
        boundary_hit = False
        if self.is_running:
            scaled_delta_time = delta_time * self.time_scale
            if self.current_scenario == "Scenario Free":
                steering = float(arcade.key.D in self.pressed_keys) - float(
                    arcade.key.A in self.pressed_keys
                )
                boundary_hit = self.world.update_free_drive(
                    scaled_delta_time,
                    throttle=arcade.key.W in self.pressed_keys,
                    brake=arcade.key.S in self.pressed_keys,
                    steering=steering,
                )
            else:
                boundary_hit = self.world.update(scaled_delta_time)

        if boundary_hit:
            self.is_running = False
            self.world.stop_free_drive_controls()
            print("Simulation paused: the vehicle reached the world boundary.")

        self._print_prediction_debug_if_changed()

    def on_draw(self) -> None:
        self.clear()
        self.world.draw()
        arcade.draw_lbwh_rectangle_filled(
            0, self.height - TOOLBAR_HEIGHT, self.width, TOOLBAR_HEIGHT, (31, 38, 48)
        )
        arcade.draw_line(
            0,
            self.height - TOOLBAR_HEIGHT,
            self.width,
            self.height - TOOLBAR_HEIGHT,
            (80, 91, 105),
            2,
        )
        self._draw_current_course_prediction()
        self._draw_vehicle_hud(show_controls=self.current_scenario == "Scenario Free")
        self.manager.draw()

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol in {arcade.key.W, arcade.key.A, arcade.key.S, arcade.key.D}:
            self.pressed_keys.add(symbol)

    def on_key_release(self, symbol: int, modifiers: int) -> None:
        self.pressed_keys.discard(symbol)

    @staticmethod
    def _create_hud_texts() -> dict[str, arcade.Text]:
        def text(font_size: int, *, anchor_x: str = "left", bold: bool = False) -> arcade.Text:
            return arcade.Text(
                "",
                0,
                0,
                (238, 243, 248),
                font_size,
                anchor_x=anchor_x,
                anchor_y="center",
                bold=bold,
            )

        return {
            "title": text(11, bold=True),
            "speed": text(28, anchor_x="right", bold=True),
            "unit": text(10),
            "steering_title": text(9),
            "steering_value": text(10, anchor_x="center", bold=True),
            "brake": text(10, bold=True),
            "danger": text(10, bold=True),
            "controls_title": text(9, bold=True),
            "control_w": text(9),
            "control_s": text(9),
            "control_ad": text(9),
        }

    def _set_hud_text(self, name: str, content: str, x: float, y: float) -> None:
        text = self._hud_texts[name]
        text.text = content
        text.x = x
        text.y = y
        text.draw()

    @staticmethod
    def _create_prediction_texts() -> dict[str, arcade.Text]:
        texts = {
            "title": arcade.Text("", 0, 0, (238, 243, 248), 11, bold=True),
            "subtitle": arcade.Text("", 0, 0, (155, 170, 185), 8),
            "status": arcade.Text("", 0, 0, (238, 243, 248), 10, bold=True),
        }
        for index in range(7):
            texts[f"detail_{index}"] = arcade.Text(
                "", 0, 0, (210, 218, 226), 9
            )
        return texts

    def _set_prediction_text(
        self,
        name: str,
        content: str,
        x: float,
        y: float,
        color: tuple[int, int, int] | None = None,
    ) -> None:
        text = self._prediction_texts[name]
        text.text = content
        text.x = x
        text.y = y
        if color is not None:
            text.color = color
        text.draw()

    @staticmethod
    def _demographic_lines(casualties: list[Pedestrian]) -> list[str]:
        labels = {
            "man": "Adult (M)",
            "woman": "Adult (F)",
            "old_man": "Senior (M)",
            "old_woman": "Senior (F)",
            "boy": "Child (M)",
            "girl": "Child (F)",
            "custom": "Custom",
        }
        counts: dict[str, int] = {}
        for pedestrian in casualties:
            label = labels[pedestrian.model]
            counts[label] = counts.get(label, 0) + 1

        if not counts:
            return ["No casualties predicted"]
        return [f"{label}: {count}" for label, count in counts.items()]

    @staticmethod
    def _person_description(person: Pedestrian) -> str:
        descriptions = {
            "man": "Adult (♂)",
            "woman": "Adult (♀)",
            "old_man": "Senior (♂)",
            "old_woman": "Senior (♀)",
            "boy": "Child (♂)",
            "girl": "Child (♀)",
            "custom": f"Custom [{person.label or 'unnamed'}]",
        }
        return descriptions[person.model]

    def _print_prediction_debug_if_changed(self) -> None:
        outcomes = self.world.predict_action_outcomes(seconds=2.0)
        signature = tuple(
            (action, tuple(id(person) for person in casualties))
            for action, casualties in outcomes.items()
        )
        if signature == self._last_debug_prediction:
            return
        self._last_debug_prediction = signature

        stop_time, stop_distance = self.world.braking_metrics()
        print(f"\n[PREDICTION DEBUG] {self.current_scenario} — next 2 seconds")
        for action, casualties in outcomes.items():
            people = ", ".join(self._person_description(person) for person in casualties)
            result = people if people else "no casualties"
            extra = (
                f" | stop time {stop_time:.2f}s, stop distance {stop_distance:.1f}px"
                if action == "Brake only"
                else ""
            )
            print(f"  {action}: {len(casualties)} kill(s) — {result}{extra}")

    def _draw_current_course_prediction(self) -> None:
        casualties = self.world.predict_current_course_casualties(seconds=2.0)
        panel_left = 14
        panel_width = 300
        panel_height = 250
        panel_top = self.height - TOOLBAR_HEIGHT - 14
        panel_bottom = panel_top - panel_height
        content_left = panel_left + 16
        collision = bool(casualties)
        accent = (238, 68, 68) if collision else (79, 196, 123)

        arcade.draw_lbwh_rectangle_filled(
            panel_left,
            panel_bottom,
            panel_width,
            panel_height,
            (18, 24, 32, 232),
        )
        arcade.draw_lbwh_rectangle_outline(
            panel_left,
            panel_bottom,
            panel_width,
            panel_height,
            (78, 96, 115),
            1,
        )
        arcade.draw_lbwh_rectangle_filled(panel_left, panel_top - 4, panel_width, 4, accent)
        self._set_prediction_text("title", "PROJECTED KILLS · 2s", content_left, panel_top - 26)
        self._set_prediction_text(
            "subtitle",
            "IF THE CURRENT COURSE CONTINUES",
            content_left,
            panel_top - 43,
        )
        card_top = panel_top - 58
        card_bottom = panel_bottom + 15
        card_color = (69, 30, 35, 235) if collision else (27, 52, 45, 235)
        arcade.draw_lbwh_rectangle_filled(
            content_left,
            card_bottom,
            panel_width - 32,
            card_top - card_bottom,
            card_color,
        )
        arcade.draw_lbwh_rectangle_filled(
            content_left, card_bottom, 4, card_top - card_bottom, accent
        )
        status = (
            f"COLLISION · {len(casualties)} KILL{'S' if len(casualties) != 1 else ''}"
            if collision
            else "SAFE · 0 KILLS"
        )
        self._set_prediction_text("status", status, content_left + 13, card_top - 25, accent)
        for index, detail in enumerate(self._demographic_lines(casualties)):
            self._set_prediction_text(
                f"detail_{index}",
                detail,
                content_left + 13,
                card_top - 51 - index * 18,
                (210, 218, 226),
            )

    def _draw_vehicle_hud(self, show_controls: bool) -> None:
        car = self.world.cars[0]
        speed_kmh = abs(car.speed) * 0.18
        right_steering = max(0.0, car.steering_percent)
        left_steering = max(0.0, -car.steering_percent)

        panel_width = 278
        panel_height = 317 if show_controls else 232
        panel_left = self.width - panel_width - 14
        panel_bottom = self.height - TOOLBAR_HEIGHT - panel_height - 14
        panel_top = panel_bottom + panel_height
        content_left = panel_left + 18
        content_right = panel_left + panel_width - 18

        arcade.draw_lbwh_rectangle_filled(
            panel_left,
            panel_bottom,
            panel_width,
            panel_height,
            (18, 24, 32, 232),
        )
        arcade.draw_lbwh_rectangle_outline(
            panel_left,
            panel_bottom,
            panel_width,
            panel_height,
            (78, 96, 115),
            1,
        )
        arcade.draw_lbwh_rectangle_filled(panel_left, panel_top - 4, panel_width, 4, (42, 177, 230))

        self._set_hud_text("title", "VEHICLE STATUS", content_left, panel_top - 25)
        self._set_hud_text("speed", f"{speed_kmh:04.1f}", content_right - 47, panel_top - 65)
        self._set_hud_text("unit", "km/h", content_right - 39, panel_top - 65)

        speed_bar_y = panel_top - 93
        speed_bar_width = panel_width - 36
        speed_ratio = min(speed_kmh / 50.0, 1.0)
        arcade.draw_lbwh_rectangle_filled(
            content_left, speed_bar_y, speed_bar_width, 8, (50, 61, 73)
        )
        arcade.draw_lbwh_rectangle_filled(
            content_left,
            speed_bar_y,
            speed_bar_width * speed_ratio,
            8,
            (42, 177, 230),
        )

        self._set_hud_text("steering_title", "STEERING", content_left, panel_top - 118)
        steering_center = panel_left + panel_width / 2
        steering_y = panel_top - 143
        half_steering_width = 105
        arcade.draw_lbwh_rectangle_filled(
            steering_center - half_steering_width,
            steering_y,
            half_steering_width * 2,
            7,
            (50, 61, 73),
        )
        arcade.draw_lbwh_rectangle_filled(steering_center - 1, steering_y - 3, 2, 13, (210, 220, 230))
        if left_steering:
            fill = half_steering_width * left_steering / 100
            arcade.draw_lbwh_rectangle_filled(
                steering_center - fill, steering_y, fill, 7, (245, 170, 55)
            )
        if right_steering:
            fill = half_steering_width * right_steering / 100
            arcade.draw_lbwh_rectangle_filled(
                steering_center, steering_y, fill, 7, (245, 170, 55)
            )
        self._set_hud_text(
            "steering_value",
            f"LEFT {left_steering:.0f}%     {right_steering:.0f}% RIGHT",
            steering_center,
            panel_top - 162,
        )

        brake_color = (230, 72, 72) if car.brake_active else (79, 196, 123)
        arcade.draw_circle_filled(content_left + 6, panel_top - 185, 6, brake_color)
        brake_status = "ACTIVE" if car.brake_active else "INACTIVE"
        self._set_hud_text("brake", f"BRAKE  {brake_status}", content_left + 20, panel_top - 185)

        danger = self.world.has_imminent_collision(seconds=2.0)
        danger_color = (238, 68, 68) if danger else (79, 196, 123)
        danger_text = "DANGER: COLLISION WITHIN 2s" if danger else "PATH CLEAR FOR 2s"
        arcade.draw_circle_filled(content_left + 6, panel_top - 211, 6, danger_color)
        self._set_hud_text("danger", danger_text, content_left + 20, panel_top - 211)

        if show_controls:
            separator_y = panel_top - 234
            arcade.draw_line(content_left, separator_y, content_right, separator_y, (65, 78, 92), 1)
            self._set_hud_text("controls_title", "CONTROLS", content_left, panel_top - 252)
            self._set_hud_text("control_w", "W       accelerate", content_left, panel_top - 270)
            self._set_hud_text("control_s", "S        brake", content_left, panel_top - 286)
            self._set_hud_text("control_ad", "A / D   steer", content_left, panel_top - 302)

    def on_resize(self, width: int, height: int) -> None:
        super().on_resize(width, height)
        # Arcade may dispatch an initial resize while Window is being constructed.
        if hasattr(self, "world"):
            self.world.resize(width, height)

    def on_close(self) -> None:
        self.manager.disable()
        super().on_close()


def main() -> None:
    SimulationWindow()
    arcade.run()


if __name__ == "__main__":
    main()
