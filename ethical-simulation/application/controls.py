"""Toolbar construction and interactive simulation controls."""

from __future__ import annotations

import arcade
import arcade.gui

from decision_engine import CODE_MODE, LLM_MODE
from ethics.utils.config import (
    FRAMEWORK_IMPLEMENTATIONS,
    FRAMEWORK_OPTIONS,
    FRAMEWORKS,
    UTILITARIANISM,
)
from scenarios import RANDOM_SCENARIO_NAME
from simulation.config import (
    MAX_CONFIGURABLE_DECISION_DISTANCE,
    MAX_CONFIGURABLE_LANE_CHANGES,
    MAX_CONFIGURABLE_VEHICLE_SPEED_KMH,
    MAX_CONFIGURABLE_VISION_DISTANCE,
    MIN_CONFIGURABLE_DECISION_DISTANCE,
    MIN_CONFIGURABLE_VISION_DISTANCE,
)
from ui.theme import FRAMEWORK_SELECTION, SCENARIO_SELECTION, dropdown_styles


class SimulationControlsMixin:
    """Provide toolbar callbacks and vehicle-control synchronization."""

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

        row = arcade.gui.UIBoxLayout(vertical=False, space_between=4)

        selection_controls = arcade.gui.UIBoxLayout(vertical=False, space_between=4)
        framework = selection_controls.add(
            arcade.gui.UIDropdown(
                default=self._framework_option(
                    self.current_framework,
                    self.current_implementation,
                ),
                options=FRAMEWORK_OPTIONS,
                width=160,
                height=34,
                **dropdown_styles(FRAMEWORK_SELECTION),
            )
        )
        scenario = selection_controls.add(
            arcade.gui.UIDropdown(
                default=self.current_scenario,
                options=self.scenario_names,
                width=132,
                height=34,
                **dropdown_styles(SCENARIO_SELECTION),
            )
        )
        automated_button = selection_controls.add(
            arcade.gui.UIFlatButton(
                text="Automated Simulation",
                width=175,
                height=34,
            )
        )
        automated_button.on_click = self._open_automated_settings
        row.add(section("FRAMEWORK / SIMULATION", selection_controls, 475))
        row.add(separator())

        playback_controls = arcade.gui.UIBoxLayout(vertical=False, space_between=5)
        time_holder, self.time_scale_label = fixed_label(
            f"x{self.time_scale:.2f}", 32
        )
        playback_controls.add(time_holder)
        time_slider = playback_controls.add(
            arcade.gui.UISlider(
                value=self.time_scale,
                min_value=0.25,
                max_value=2.0,
                step=0.25,
                width=60,
                height=26,
            )
        )
        reset_label = (
            "Regenerate"
            if self.current_scenario == RANDOM_SCENARIO_NAME
            else "Reset"
        )
        for label, handler, width in (
            (">", self._play, 34),
            ("||", self._pause, 34),
            (reset_label, self._stop, 78),
        ):
            button = playback_controls.add(
                arcade.gui.UIFlatButton(text=label, width=width, height=34)
            )
            button.on_click = handler
            if handler == self._stop:
                self.reset_button = button
        row.add(section("TIME / CONTROLS", playback_controls, 256))
        row.add(separator())

        vehicle_controls = arcade.gui.UIBoxLayout(vertical=False, space_between=4)
        initial_kmh = self.scenario_initial_speeds[self.current_scenario]
        initial_holder, self.initial_speed_label = fixed_label(
            f"Speed {initial_kmh:02.0f}", 44, font_size=8
        )
        vehicle_controls.add(initial_holder)
        self.initial_speed_slider = vehicle_controls.add(
            arcade.gui.UISlider(
                value=initial_kmh,
                min_value=0,
                max_value=MAX_CONFIGURABLE_VEHICLE_SPEED_KMH,
                step=1,
                width=34,
                height=26,
            )
        )
        vision_holder, self.vision_distance_label = fixed_label(
            f"Vision {self.vision_distance:.0f}",
            50,
            font_size=8,
        )
        vehicle_controls.add(vision_holder)
        self.vision_distance_slider = vehicle_controls.add(
            arcade.gui.UISlider(
                value=self.vision_distance,
                min_value=MIN_CONFIGURABLE_VISION_DISTANCE,
                max_value=MAX_CONFIGURABLE_VISION_DISTANCE,
                step=10,
                width=34,
                height=26,
            )
        )
        decision_holder, self.decision_distance_label = fixed_label(
            f"Decision {self.decision_distance:.0f}",
            58,
            font_size=8,
        )
        vehicle_controls.add(decision_holder)
        self.decision_distance_slider = vehicle_controls.add(
            arcade.gui.UISlider(
                value=self.decision_distance,
                min_value=MIN_CONFIGURABLE_DECISION_DISTANCE,
                max_value=MAX_CONFIGURABLE_DECISION_DISTANCE,
                step=10,
                width=34,
                height=26,
            )
        )
        shifts_holder, self.max_spostamenti_label = fixed_label(
            f"Max shifts {self.max_spostamenti}",
            48,
            font_size=8,
        )
        vehicle_controls.add(shifts_holder)
        self.max_spostamenti_slider = vehicle_controls.add(
            arcade.gui.UISlider(
                value=self.max_spostamenti,
                min_value=0,
                max_value=MAX_CONFIGURABLE_LANE_CHANGES,
                step=1,
                width=32,
                height=26,
            )
        )
        row.add(section("VEHICLE VARIABLES", vehicle_controls, 362))
        row.add(separator())

        app_controls = arcade.gui.UIBoxLayout(vertical=False, space_between=5)
        menu_button = app_controls.add(
            arcade.gui.UIFlatButton(text="Menu", width=65, height=34)
        )
        menu_button.on_click = self._open_menu
        row.add(section("APPLICATION", app_controls, 65))

        framework.on_change = self._framework_changed
        scenario.on_change = self._scenario_changed
        time_slider.on_change = self._time_scale_changed
        self.initial_speed_slider.on_change = self._initial_speed_changed
        self.vision_distance_slider.on_change = self._vision_distance_changed
        self.decision_distance_slider.on_change = self._decision_distance_changed
        self.max_spostamenti_slider.on_change = self._max_spostamenti_changed
        anchor = arcade.gui.UIAnchorLayout()
        anchor.add(row, anchor_x="center", anchor_y="top", align_y=-8)
        self.manager.add(anchor)

    def _framework_changed(self, event: arcade.gui.UIOnChangeEvent) -> None:
        if event.new_value is not None:
            framework_name, implementation = self._parse_framework_option(
                str(event.new_value)
            )
            self._cancel_pending_decision()
            self.current_framework = framework_name
            self.current_implementation = implementation
            self.last_decision = None
            self._configure_simulation_engine()

    @staticmethod
    def _framework_option(framework_name: str, implementation: str) -> str:
        return f"{framework_name} ({implementation})"

    @staticmethod
    def _parse_framework_option(option: str) -> tuple[str, str]:
        for implementation in (LLM_MODE, CODE_MODE):
            suffix = f" ({implementation})"
            if option.endswith(suffix):
                framework_name = option[: -len(suffix)]
                if framework_name in FRAMEWORKS:
                    allowed = FRAMEWORK_IMPLEMENTATIONS[framework_name]
                    if implementation in allowed:
                        return framework_name, implementation
                    return framework_name, allowed[0]
        return UTILITARIANISM, CODE_MODE

    def _reset_framework_state(self) -> None:
        for framework in self.ethical_frameworks.values():
            framework.reset()

    def _reset_run_state(self) -> None:
        self._cancel_pending_decision()
        self.is_running = False
        self.simulation_finished = False
        self._reset_framework_state()
        self._configure_simulation_engine()
        self.simulation_engine.reset(reset_framework=False)
        self._sync_simulation_engine_state()

    def _apply_current_scenario_vehicle_settings(self) -> None:
        """Apply fixed settings or adopt values resolved by Random Scenario."""
        car = self.world.primary_car
        if car is None:
            return
        if self.current_scenario == RANDOM_SCENARIO_NAME:
            self.vision_distance = self.world.vision_distance
            self.decision_distance = self.world.decision_distance
            self.max_spostamenti = self.world.max_spostamenti
            self.scenario_initial_speeds[RANDOM_SCENARIO_NAME] = car.speed
        else:
            self.vision_distance = self.fixed_vision_distance
            self.decision_distance = self.fixed_decision_distance
            self.max_spostamenti = self.fixed_max_spostamenti
            self.world.configure_vehicle(
                vision_distance=self.vision_distance,
                decision_distance=self.decision_distance,
                max_spostamenti=self.max_spostamenti,
            )
            car.speed = self.scenario_initial_speeds[self.current_scenario]

    def _sync_vehicle_control_values(self) -> None:
        """Refresh toolbar widgets after a scenario resolves random values."""
        car = self.world.primary_car
        if car is None or not hasattr(self, "initial_speed_slider"):
            return
        self.initial_speed_slider.value = car.speed
        self.initial_speed_label.text = f"Speed {car.speed:02.0f}"
        self.vision_distance_slider.value = self.vision_distance
        self.vision_distance_label.text = f"Vision {self.vision_distance:.0f}"
        self.decision_distance_slider.value = self.decision_distance
        self.decision_distance_label.text = (
            f"Decision {self.decision_distance:.0f}"
        )
        self.max_spostamenti_slider.value = self.max_spostamenti
        self.max_spostamenti_label.text = f"Max shifts {self.max_spostamenti}"

    def _scenario_changed(self, event: arcade.gui.UIOnChangeEvent) -> None:
        if event.new_value is not None:
            self.current_scenario = event.new_value
            self.world.reset(self.current_scenario)
            self._apply_current_scenario_vehicle_settings()
            self._sync_vehicle_control_values()
            self.reset_button.text = (
                "Regenerate"
                if self.current_scenario == RANDOM_SCENARIO_NAME
                else "Reset"
            )
            self.reset_button.trigger_render()
            self._reset_run_state()

    def _time_scale_changed(self, event: arcade.gui.UIOnChangeEvent) -> None:
        if event.new_value is not None:
            self.time_scale = float(event.new_value)
            self.time_scale_label.text = f"x{self.time_scale:.2f}"

    def _initial_speed_changed(self, event: arcade.gui.UIOnChangeEvent) -> None:
        if event.new_value is not None:
            speed_kmh = float(event.new_value)
            self.scenario_initial_speeds[self.current_scenario] = speed_kmh
            self.world.cars[0].speed = speed_kmh
            self.initial_speed_label.text = f"Speed {speed_kmh:02.0f}"

    def _vision_distance_changed(self, event: arcade.gui.UIOnChangeEvent) -> None:
        if event.new_value is not None:
            self.vision_distance = float(event.new_value)
            if self.decision_distance > self.vision_distance:
                self.decision_distance = self.vision_distance
                self.decision_distance_slider.value = self.decision_distance
                self.decision_distance_label.text = (
                    f"Decision {self.decision_distance:.0f}"
                )
            self.vision_distance_label.text = f"Vision {self.vision_distance:.0f}"
            self.world.configure_vehicle(
                vision_distance=self.vision_distance,
                decision_distance=self.decision_distance,
            )
            if self.current_scenario != RANDOM_SCENARIO_NAME:
                self.fixed_vision_distance = self.vision_distance
                self.fixed_decision_distance = self.decision_distance

    def _decision_distance_changed(self, event: arcade.gui.UIOnChangeEvent) -> None:
        if event.new_value is not None:
            requested_distance = float(event.new_value)
            self.decision_distance = min(requested_distance, self.vision_distance)
            if requested_distance != self.decision_distance:
                self.decision_distance_slider.value = self.decision_distance
            self.decision_distance_label.text = (
                f"Decision {self.decision_distance:.0f}"
            )
            self.world.configure_vehicle(
                decision_distance=self.decision_distance,
            )
            if self.current_scenario != RANDOM_SCENARIO_NAME:
                self.fixed_decision_distance = self.decision_distance

    def _max_spostamenti_changed(self, event: arcade.gui.UIOnChangeEvent) -> None:
        if event.new_value is not None:
            requested_max = int(round(float(event.new_value)))
            self.world.configure_vehicle(max_spostamenti=requested_max)
            self.max_spostamenti = self.world.max_spostamenti
            if requested_max != self.max_spostamenti:
                self.max_spostamenti_slider.value = self.max_spostamenti
            self.max_spostamenti_label.text = f"Max shifts {self.max_spostamenti}"
            if self.current_scenario != RANDOM_SCENARIO_NAME:
                self.fixed_max_spostamenti = self.max_spostamenti

    def _play(self, _event: arcade.gui.UIOnClickEvent) -> None:
        if self.simulation_finished:
            return
        self.is_running = True

    def _pause(self, _event: arcade.gui.UIOnClickEvent) -> None:
        self.is_running = False
