"""Interactive entry point for Ethical Multi-Agent Simulation."""

import math
import webbrowser

import arcade
import arcade.gui

from ethics.utilitarian import DEFAULT_ENTITIES_VALUES
from ethics.constant import ConstantFramework
from ethics.kant import KantFramework
from ethics.ross import RossFramework
from ethics.utilitarian import UtilitarianFramework
from simulation import World
from simulation.entities import Pedestrian
from ui.screens import (
    build_framework_settings,
    build_info,
    build_menu,
    build_placeholder,
)

SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
TOOLBAR_HEIGHT = 72

FRAMEWORKS = ["Utilitarianism", "Kant", "Constant", "Ross", "Virtue Ethics"]
SCENARIOS = ["Scenario 1", "Scenario 2", "Scenario Free"]
GITHUB_REPOSITORY = "https://github.com/lucaAnza/Ethics_Multi-Agent_Simulation"


class SimulationWindow(arcade.Window):
    def __init__(self) -> None:
        super().__init__(
            SCREEN_WIDTH,
            SCREEN_HEIGHT,
            "Ethical Multi-Agent Simulation",
            resizable=True,
        )
        self.set_minimum_size(1150, 500)
        self.current_framework = "Utilitarianism"
        self.current_scenario = "Scenario 1"
        self.active_screen = "simulation"
        self.is_running = False
        self.time_scale = 1.0
        self.new_decision_wait = 1.0
        self.active_decision: str | None = None
        self.decision_wait_remaining = 0.0
        self.simulation_has_started = False
        self.simulation_had_motion = False
        self.simulation_finished = False
        self.pressed_keys: set[int] = set()
        self._last_alert_prediction: tuple[int, ...] | None = None
        self._last_decision_alert: tuple[int, ...] | None = None

        self.world = World(self.width, self.height, self.current_scenario)
        self.framework_settings = {
            "Utilitarianism": dict(DEFAULT_ENTITIES_VALUES),
        }
        self.ethical_frameworks = {
            "Utilitarianism": UtilitarianFramework(
                self.framework_settings["Utilitarianism"]
            ),
            "Kant": KantFramework(),
            "Constant": ConstantFramework(),
            "Ross": RossFramework(),
        }
        self.world.framework_parameters = self.framework_settings
        self.utilitarian_entity_inputs: dict[str, arcade.gui.UIInputText] = {}
        self.framework_status_label: arcade.gui.UILabel | None = None
        self.scenario_initial_speeds = {
            "Scenario 1": 120.0,
            "Scenario 2": 120.0,
            "Scenario Free": 0.0,
        }
        self._hud_texts = self._create_hud_texts()
        self._prediction_texts = self._create_prediction_texts()
        self._end_texts = self._create_end_texts()
        self.manager = arcade.gui.UIManager()
        self._setup_toolbar()
        self.manager.enable()
        arcade.set_background_color((91, 145, 79))

    def _setup_toolbar(self) -> None:
        def section(title: str, controls: arcade.gui.UIBoxLayout, width: int):
            layout = arcade.gui.UIBoxLayout(vertical=True, space_between=3)
            layout.add(
                arcade.gui.UILabel(
                    text=title,
                    width=width,
                    height=13,
                    font_size=8,
                    text_color=(155, 170, 185),
                )
            )
            layout.add(controls)
            return layout

        def separator():
            return arcade.gui.UIWidget(width=1, height=50).with_background(
                color=(78, 91, 105)
            )

        def fixed_label(text: str, width: int, font_size: int = 10):
            """Keep changing text from resizing the surrounding toolbar layout."""
            holder = arcade.gui.UIAnchorLayout(
                width=width,
                height=34,
                size_hint_min=(width, 34),
                size_hint_max=(width, 34),
            )
            label = arcade.gui.UILabel(text=text, height=34, font_size=font_size)
            holder.add(label, anchor_x="left", anchor_y="center")
            return holder, label

        row = arcade.gui.UIBoxLayout(vertical=False, space_between=20)

        selection_controls = arcade.gui.UIBoxLayout(vertical=False, space_between=5)
        framework = selection_controls.add(
            arcade.gui.UIDropdown(
                default=self.current_framework, options=FRAMEWORKS, width=135, height=34
            )
        )
        scenario = selection_controls.add(
            arcade.gui.UIDropdown(
                default=self.current_scenario, options=SCENARIOS, width=110, height=34
            )
        )
        row.add(section("FRAMEWORK / SIMULATION", selection_controls, 250))
        row.add(separator())

        playback_controls = arcade.gui.UIBoxLayout(vertical=False, space_between=5)
        time_holder, self.time_scale_label = fixed_label(
            f"Time x{self.time_scale:.2f}", 62
        )
        playback_controls.add(time_holder)
        time_slider = playback_controls.add(
            arcade.gui.UISlider(
                value=self.time_scale,
                min_value=0.25,
                max_value=2.0,
                step=0.25,
                width=75,
                height=26,
            )
        )
        for label, handler, width in (
            ("play", self._play, 38),
            ("||", self._pause, 38),
            ("reset", self._stop, 38),
        ):
            button = playback_controls.add(
                arcade.gui.UIFlatButton(text=label, width=width, height=34)
            )
            button.on_click = handler
        row.add(section("TIME / CONTROLS", playback_controls, 271))
        row.add(separator())

        vehicle_controls = arcade.gui.UIBoxLayout(vertical=False, space_between=5)
        initial_kmh = self.scenario_initial_speeds[self.current_scenario] * 0.18
        initial_holder, self.initial_speed_label = fixed_label(
            f"Initial {initial_kmh:02.0f}", 70
        )
        vehicle_controls.add(initial_holder)
        self.initial_speed_slider = vehicle_controls.add(
            arcade.gui.UISlider(
                value=initial_kmh,
                min_value=0,
                max_value=50,
                step=1,
                width=75,
                height=26,
            )
        )
        wait_holder, self.new_decision_wait_label = fixed_label(
            f"new_decision_wait {self.new_decision_wait:.2f}s",
            135,
            font_size=8,
        )
        vehicle_controls.add(wait_holder)
        new_decision_wait_slider = vehicle_controls.add(
            arcade.gui.UISlider(
                value=self.new_decision_wait,
                min_value=0.25,
                max_value=3.0,
                step=0.25,
                width=65,
                height=26,
            )
        )
        row.add(section("VEHICLE VARIABLES", vehicle_controls, 360))
        row.add(separator())

        app_controls = arcade.gui.UIBoxLayout(vertical=False, space_between=5)
        menu_button = app_controls.add(
            arcade.gui.UIFlatButton(text="Menu", width=125, height=34)
        )
        menu_button.on_click = self._open_menu
        row.add(section("APPLICATION", app_controls, 125))

        framework.on_change = self._framework_changed
        scenario.on_change = self._scenario_changed
        time_slider.on_change = self._time_scale_changed
        self.initial_speed_slider.on_change = self._initial_speed_changed
        new_decision_wait_slider.on_change = self._new_decision_wait_changed
        anchor = arcade.gui.UIAnchorLayout()
        anchor.add(row, anchor_x="center", anchor_y="top", align_y=-8)
        self.manager.add(anchor)

    def _framework_changed(self, event: arcade.gui.UIOnChangeEvent) -> None:
        if event.new_value is not None:
            self.current_framework = event.new_value
            self._reset_active_decision()

    def _scenario_changed(self, event: arcade.gui.UIOnChangeEvent) -> None:
        if event.new_value is not None:
            self.current_scenario = event.new_value
            self.pressed_keys.clear()
            self.world.reset(self.current_scenario)
            speed = self.scenario_initial_speeds[self.current_scenario]
            self.world.cars[0].speed = speed
            self.initial_speed_slider.value = speed * 0.18
            self.initial_speed_label.text = f"Initial {speed * 0.18:02.0f}"
            self._last_alert_prediction = None
            self._reset_active_decision()
            self.simulation_has_started = False
            self.simulation_had_motion = False
            self.simulation_finished = False

    def _time_scale_changed(self, event: arcade.gui.UIOnChangeEvent) -> None:
        if event.new_value is not None:
            self.time_scale = float(event.new_value)
            self.time_scale_label.text = f"Time x{self.time_scale:.2f}"

    def _initial_speed_changed(self, event: arcade.gui.UIOnChangeEvent) -> None:
        if event.new_value is not None:
            speed_kmh = float(event.new_value)
            speed = speed_kmh / 0.18
            self.scenario_initial_speeds[self.current_scenario] = speed
            self.world.cars[0].speed = speed
            self.initial_speed_label.text = f"Initial {speed_kmh:02.0f}"
            self._last_alert_prediction = None
            self.simulation_has_started = False
            self.simulation_had_motion = False
            self.simulation_finished = False

    def _new_decision_wait_changed(self, event: arcade.gui.UIOnChangeEvent) -> None:
        if event.new_value is not None:
            self.new_decision_wait = float(event.new_value)
            self.new_decision_wait_label.text = (
                f"new_decision_wait {self.new_decision_wait:.2f}s"
            )

    def _play(self, _event: arcade.gui.UIOnClickEvent) -> None:
        if self.simulation_finished:
            return
        self.simulation_has_started = True
        self.is_running = True

    def _pause(self, _event: arcade.gui.UIOnClickEvent) -> None:
        self.is_running = False
        self.world.stop_free_drive_controls()

    def _reset_active_decision(self) -> None:
        self.active_decision = None
        self.decision_wait_remaining = 0.0
        self._last_decision_alert = None
        self.world.stop_free_drive_controls()

    def _maybe_trigger_ethical_decision(self) -> None:
        casualties = self.world.predict_current_course_casualties(seconds=2.0)
        alert_signature = tuple(id(person) for person in casualties)
        if not casualties:
            self._last_decision_alert = None
            return
        if self.active_decision is not None:
            return
        if alert_signature == self._last_decision_alert:
            return

        self._last_decision_alert = alert_signature
        decision_state = self.world.build_ethical_decision_state(seconds=2.0)
        framework = self.ethical_frameworks.get(self.current_framework)
        decision = framework.decide(decision_state) if framework else "continue"
        valid_decisions = {"continue", "steer_right", "steer_left", "brake"}
        if decision not in valid_decisions:
            decision = "continue"

        print(f"\n[ETHICAL DECISION] Framework: {self.current_framework}")
        for alternative in decision_state["alternatives"]:
            print(
                f"  {alternative['action']}: "
                f"{len(alternative['casualties'])} predicted kill(s)"
            )
        print(f"  Selected action: {decision}")

        if decision != "continue":
            self.active_decision = decision
            self.decision_wait_remaining = self.new_decision_wait

    def _stop(self, _event: arcade.gui.UIOnClickEvent) -> None:
        self.is_running = False
        self.pressed_keys.clear()
        self.world.reset()
        self.world.cars[0].speed = self.scenario_initial_speeds[self.current_scenario]
        self.world.stop_free_drive_controls()
        self._last_alert_prediction = None
        self._reset_active_decision()
        self.simulation_has_started = False
        self.simulation_had_motion = False
        self.simulation_finished = False

    def _show_simulation_end(self) -> None:
        self.is_running = False
        self.simulation_finished = True
        self._reset_active_decision()
        self.manager.clear()

        dead_count = len(self.world.dead_pedestrians())
        panel_height = 178 + dead_count * 20
        reset_button = arcade.gui.UIFlatButton(
            text="Reset",
            width=190,
            height=42,
            style=arcade.gui.UIFlatButton.STYLE_BLUE,
        )
        reset_button.on_click = self._reset_from_end
        anchor = arcade.gui.UIAnchorLayout()
        anchor.add(
            reset_button,
            anchor_x="center",
            anchor_y="center",
            align_y=-panel_height / 2 + 54,
        )
        self.manager.add(anchor)

    def _reset_from_end(self, event: arcade.gui.UIOnClickEvent) -> None:
        self._stop(event)
        self.manager.clear()
        self._setup_toolbar()

    def _open_menu(self, _event: arcade.gui.UIOnClickEvent | None = None) -> None:
        self._pause(None)
        self.pressed_keys.clear()
        self.active_screen = "menu"
        self.manager.clear()
        build_menu(
            self.manager,
            on_framework=self._open_framework_settings,
            on_scenario=self._open_scenario_settings,
            on_general=self._open_general_settings,
            on_info=self._open_info,
            on_back=self._return_to_simulation,
        )

    def _return_to_simulation(
        self, _event: arcade.gui.UIOnClickEvent | None = None
    ) -> None:
        self.active_screen = "simulation"
        self.manager.clear()
        self._setup_toolbar()

    def _open_framework_settings(
        self, _event: arcade.gui.UIOnClickEvent | None = None
    ) -> None:
        selected = (
            self.current_framework
            if self.current_framework in FRAMEWORKS
            else "Utilitarianism"
        )
        self._show_framework_editor(selected)

    def _show_framework_editor(self, framework_name: str) -> None:
        self.active_screen = "framework_settings"
        self.manager.clear()
        (
            self.utilitarian_entity_inputs,
            self.framework_status_label,
        ) = build_framework_settings(
            self.manager,
            selected=framework_name,
            utilitarian_entity_values=self.framework_settings["Utilitarianism"],
            on_select=self._show_framework_editor,
            on_save=self._save_utilitarian_settings,
            on_back=self._open_menu,
        )

    def _save_utilitarian_settings(
        self, _event: arcade.gui.UIOnClickEvent | None = None
    ) -> None:
        parsed_values: dict[str, float] = {}
        has_error = False
        for entity_model, input_widget in self.utilitarian_entity_inputs.items():
            try:
                value = float(input_widget.text.strip())
                if not math.isfinite(value):
                    raise ValueError
            except ValueError:
                input_widget.invalid = True
                has_error = True
            else:
                input_widget.invalid = False
                parsed_values[entity_model] = value

        if self.framework_status_label is None:
            return
        if has_error:
            self.framework_status_label.text = "Enter a valid numeric value in every field."
            return

        self.framework_settings["Utilitarianism"].update(parsed_values)
        utilitarian = self.ethical_frameworks["Utilitarianism"]
        utilitarian.update_entity_values(parsed_values)
        self.framework_status_label.text = "Values saved in simulation state."

    def _open_scenario_settings(
        self, _event: arcade.gui.UIOnClickEvent | None = None
    ) -> None:
        self.active_screen = "scenario_settings"
        self.manager.clear()
        build_placeholder(
            self.manager,
            title="Scenario Settings",
            on_back=self._open_menu,
        )

    def _open_general_settings(
        self, _event: arcade.gui.UIOnClickEvent | None = None
    ) -> None:
        self.active_screen = "general_settings"
        self.manager.clear()
        build_placeholder(
            self.manager,
            title="General Settings",
            on_back=self._open_menu,
        )

    def _open_info(self, _event: arcade.gui.UIOnClickEvent | None = None) -> None:
        self.active_screen = "info"
        self.manager.clear()
        build_info(
            self.manager,
            repository_url=GITHUB_REPOSITORY,
            on_open_repository=self._open_repository,
            on_back=self._open_menu,
        )

    @staticmethod
    def _open_repository(_event: arcade.gui.UIOnClickEvent | None = None) -> None:
        webbrowser.open(GITHUB_REPOSITORY)

    def on_update(self, delta_time: float) -> None:
        if self.active_screen != "simulation":
            return

        boundary_hit = False
        if self.is_running:
            if not self.world.all_cars_stopped():
                self.simulation_had_motion = True
            scaled_delta_time = delta_time * self.time_scale
            self._maybe_trigger_ethical_decision()
            if self.active_decision is not None:
                boundary_hit = self.world.update_decision_action(
                    scaled_delta_time,
                    self.active_decision,
                )
                self.decision_wait_remaining -= scaled_delta_time
                if self.decision_wait_remaining <= 0:
                    self.active_decision = None
                    self.decision_wait_remaining = 0.0
                    self.world.stop_free_drive_controls()
            elif self.current_scenario == "Scenario Free":
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

            if not self.world.all_cars_stopped():
                self.simulation_had_motion = True

        if boundary_hit:
            self.is_running = False
            self._reset_active_decision()
            print("Simulation paused: the vehicle reached the world boundary.")

        if (
            self.simulation_has_started
            and self.simulation_had_motion
            and not self.simulation_finished
            and self.world.all_cars_stopped()
        ):
            self._show_simulation_end()

        self._print_prediction_debug_if_changed()

    def on_draw(self) -> None:
        self.clear()
        if self.active_screen != "simulation":
            self._draw_navigation_background()
            self.manager.draw()
            return

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
        if self.simulation_finished:
            self._draw_simulation_end_overlay()
        self.manager.draw()

    def _draw_navigation_background(self) -> None:
        arcade.draw_lbwh_rectangle_filled(
            0, 0, self.width, self.height, (23, 30, 39)
        )
        panel_width = min(980, self.width - 80)
        panel_height = min(650, self.height - 80)
        panel_left = (self.width - panel_width) / 2
        panel_bottom = (self.height - panel_height) / 2
        arcade.draw_lbwh_rectangle_filled(
            panel_left,
            panel_bottom,
            panel_width,
            panel_height,
            (31, 38, 48),
        )
        arcade.draw_lbwh_rectangle_outline(
            panel_left,
            panel_bottom,
            panel_width,
            panel_height,
            (78, 96, 115),
            1,
        )
        arcade.draw_lbwh_rectangle_filled(
            panel_left, panel_bottom + panel_height - 4, panel_width, 4, (42, 177, 230)
        )

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if self.active_screen != "simulation":
            if symbol == arcade.key.ESCAPE:
                if self.active_screen == "menu":
                    self._return_to_simulation()
                else:
                    self._open_menu()
            return
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

    @staticmethod
    def _create_end_texts() -> dict[str, arcade.Text]:
        texts = {
            "title": arcade.Text(
                "",
                0,
                0,
                (238, 243, 248),
                20,
                anchor_x="center",
                anchor_y="center",
                bold=True,
            ),
            "status": arcade.Text(
                "",
                0,
                0,
                (238, 243, 248),
                14,
                anchor_x="center",
                anchor_y="center",
                bold=True,
            ),
            "hint": arcade.Text(
                "",
                0,
                0,
                (155, 170, 185),
                9,
                anchor_x="center",
                anchor_y="center",
            ),
        }
        for index in range(20):
            texts[f"person_{index}"] = arcade.Text(
                "",
                0,
                0,
                (210, 218, 226),
                10,
                anchor_y="center",
            )
        return texts

    @staticmethod
    def _end_person_description(person: Pedestrian) -> str:
        descriptions = {
            "man": "Adult (M)",
            "woman": "Adult (F)",
            "old_man": "Senior (M)",
            "old_woman": "Senior (F)",
            "boy": "Child (M)",
            "girl": "Child (F)",
            "custom": f"Custom [{person.label or 'unnamed'}]",
        }
        return descriptions[person.model]

    def _draw_simulation_end_overlay(self) -> None:
        dead = self.world.dead_pedestrians()
        panel_width = 520
        panel_height = 178 + len(dead) * 20
        panel_left = (self.width - panel_width) / 2
        panel_bottom = (self.height - panel_height) / 2
        panel_top = panel_bottom + panel_height
        center_x = self.width / 2

        arcade.draw_lbwh_rectangle_filled(
            0,
            0,
            self.width,
            self.height,
            (5, 9, 14, 155),
        )
        arcade.draw_lbwh_rectangle_filled(
            panel_left,
            panel_bottom,
            panel_width,
            panel_height,
            (24, 32, 42, 250),
        )
        arcade.draw_lbwh_rectangle_outline(
            panel_left,
            panel_bottom,
            panel_width,
            panel_height,
            (90, 106, 124),
            2,
        )

        title = self._end_texts["title"]
        title.text = "SIMULATION COMPLETE"
        title.x, title.y = center_x, panel_top - 38
        title.draw()

        status = self._end_texts["status"]
        if dead:
            status.text = f"Deaths: {len(dead)}"
            status.color = (238, 68, 68)
        else:
            status.text = "Success nobody is dead!"
            status.color = (79, 196, 123)
        status.x, status.y = center_x, panel_top - 72
        status.draw()

        for index, person in enumerate(dead):
            person_text = self._end_texts[f"person_{index}"]
            person_text.text = f"{index + 1}. {self._end_person_description(person)}"
            person_text.x = panel_left + 58
            person_text.y = panel_top - 105 - index * 20
            person_text.draw()

        hint = self._end_texts["hint"]
        hint.text = "Click Reset to start a new simulation."
        hint.x, hint.y = center_x, panel_bottom + 24
        hint.draw()

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
        current_casualties = self.world.predict_current_course_casualties(seconds=2.0)
        alert_signature = tuple(
            id(person) for person in current_casualties
        )
        if alert_signature == self._last_alert_prediction:
            return
        self._last_alert_prediction = alert_signature

        outcomes = self.world.predict_action_outcomes(seconds=2.0)
        stop_time, stop_distance = self.world.braking_metrics()
        current_people = ", ".join(
            self._person_description(person) for person in current_casualties
        )
        current_result = current_people if current_people else "no casualties"
        print(f"\n[ALERT CHANGED] {self.current_scenario} — next 2 seconds")
        print(
            f"  Current course: {len(current_casualties)} kill(s) — {current_result}"
        )
        print("  Alternative actions:")
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
