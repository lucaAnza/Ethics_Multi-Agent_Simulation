"""Automated-simulation setup and batch-run navigation."""

from __future__ import annotations

from copy import deepcopy
import webbrowser

import arcade
import arcade.gui

from application.config import GITHUB_REPOSITORY
from automated import COMPARISON, ONLY_DETERMINISTIC, ONLY_LLM, BatchConfig
from automated.config import MAX_DETERMINISTIC_BATCH_RUNS, MAX_LLM_BATCH_RUNS
from ethics.utils.config import DETERMINISTIC_FRAMEWORKS, FRAMEWORKS, UTILITARIANISM
from scenarios import RANDOM_SCENARIO_NAME
from ui.screens import build_automated_progress, build_automated_settings


class AutomatedSimulationMixin:
    """Translate batch UI state into validated runner configuration."""

    def _automated_framework_options(self) -> list[str]:
        if self.automated_mode == ONLY_LLM:
            return [f"{name} LLM" for name in FRAMEWORKS]
        return list(DETERMINISTIC_FRAMEWORKS)

    def _automated_framework_display(self) -> str:
        if self.automated_mode == ONLY_LLM:
            return f"{self.automated_framework} LLM"
        return self.automated_framework

    def _remember_automated_fields(self) -> None:
        if self.automated_count_input is not None:
            self.automated_counts[self.automated_mode] = (
                self.automated_count_input.text.strip()
            )
        if self.automated_seed_input is not None:
            self.automated_seed = self.automated_seed_input.text.strip()

    def _open_automated_settings(
        self,
        _event: arcade.gui.UIOnClickEvent | None = None,
        *,
        message: str = "",
    ) -> None:
        self._pause(None)
        if self.automated_framework not in (
            FRAMEWORKS if self.automated_mode == ONLY_LLM else DETERMINISTIC_FRAMEWORKS
        ):
            self.automated_framework = UTILITARIANISM
        if self.automated_scenario not in self.scenario_names:
            self.automated_scenario = self.scenario_names[0]
        self.active_screen = "automated_settings"
        self.manager.clear()
        (
            self.automated_count_input,
            self.automated_seed_input,
            self.automated_status_label,
        ) = build_automated_settings(
            self.manager,
            mode=self.automated_mode,
            number_of_runs=self.automated_counts[self.automated_mode],
            framework=self._automated_framework_display(),
            scenario=self.automated_scenario,
            random_seed=self.automated_seed,
            random_scenario_selected=(
                self.automated_scenario == RANDOM_SCENARIO_NAME
            ),
            mode_options=[ONLY_DETERMINISTIC, ONLY_LLM, COMPARISON],
            framework_options=self._automated_framework_options(),
            scenario_options=self.scenario_names,
            message=message,
            on_mode_change=self._automated_mode_changed,
            on_framework_change=self._automated_framework_changed,
            on_scenario_change=self._automated_scenario_changed,
            on_random_scenario_settings=self._open_automated_random_settings,
            on_start=self._start_automated_batch,
            on_back=self._return_to_simulation,
        )

    def _open_automated_random_settings(
        self,
        event: arcade.gui.UIOnClickEvent | None = None,
    ) -> None:
        """Open the shared Random Scenario editor from the batch setup."""
        self._remember_automated_fields()
        self._open_scenario_settings(
            event,
            selected_scenario=RANDOM_SCENARIO_NAME,
        )

    def _automated_mode_changed(self, event: arcade.gui.UIOnChangeEvent) -> None:
        if event.new_value is None:
            return
        self._remember_automated_fields()
        self.automated_mode = str(event.new_value)
        if (
            self.automated_mode != ONLY_LLM
            and self.automated_framework not in DETERMINISTIC_FRAMEWORKS
        ):
            self.automated_framework = UTILITARIANISM
        self._open_automated_settings()

    def _automated_framework_changed(
        self,
        event: arcade.gui.UIOnChangeEvent,
    ) -> None:
        if event.new_value is not None:
            selected = str(event.new_value)
            if selected.endswith(" LLM"):
                selected = selected[:-4]
            if selected in FRAMEWORKS:
                self.automated_framework = selected

    def _automated_scenario_changed(
        self,
        event: arcade.gui.UIOnChangeEvent,
    ) -> None:
        if event.new_value is not None and event.new_value in self.scenario_names:
            self._remember_automated_fields()
            self.automated_scenario = str(event.new_value)
            self._open_automated_settings()

    def _set_automated_error(self, message: str) -> None:
        if self.automated_status_label is not None:
            self.automated_status_label.text = message

    def _build_automated_config(self) -> BatchConfig:
        self._remember_automated_fields()
        try:
            count = int(self.automated_counts[self.automated_mode])
        except ValueError as error:
            raise ValueError("Number of simulations must be an integer") from error
        maximum = (
            MAX_DETERMINISTIC_BATCH_RUNS
            if self.automated_mode == ONLY_DETERMINISTIC
            else MAX_LLM_BATCH_RUNS
        )
        if not 1 <= count <= maximum:
            raise ValueError(f"Number of simulations must be between 1 and {maximum}")
        try:
            seed = int(self.automated_seed) if self.automated_seed else None
        except ValueError as error:
            raise ValueError("Random seed must be an integer or left empty") from error
        return BatchConfig(
            mode=self.automated_mode,
            number_of_runs=count,
            framework_name=self.automated_framework,
            scenario_name=self.automated_scenario,
            random_seed=seed,
            random_scenario_settings=self.random_scenario_settings.to_dict(),
            scenario_definitions=deepcopy(self.scenario_definitions),
            framework_settings=self._framework_configuration(
                self.automated_framework
            ),
            utilitarian_values=deepcopy(
                self.framework_settings[UTILITARIANISM]
            ),
            additional_instructions=self.llm_additional_instructions.get(
                self.automated_framework,
                "",
            ),
            world_width=self.width,
            world_height=self.height,
            vision_distance=self.fixed_vision_distance,
            decision_distance=self.fixed_decision_distance,
            max_lane_changes=self.fixed_max_spostamenti,
        )

    def _start_automated_batch(
        self,
        _event: arcade.gui.UIOnClickEvent | None = None,
    ) -> None:
        try:
            config = self._build_automated_config()
            self.automated_runner.start(config)
        except (RuntimeError, ValueError) as error:
            self._set_automated_error(str(error))
            return
        self.last_batch_config = config
        self.batch_report = None
        self.active_screen = "automated_progress"
        self.manager.clear()
        self.automated_cancel_button = build_automated_progress(
            self.manager,
            on_cancel=self._cancel_automated_batch,
        )

    def _cancel_automated_batch(
        self,
        _event: arcade.gui.UIOnClickEvent | None = None,
    ) -> None:
        self.automated_runner.cancel()
        if self.automated_cancel_button is not None:
            self.automated_cancel_button.text = "Cancelling..."
            self.automated_cancel_button.disabled = True

    def _restart_automated_batch(
        self,
        _event: arcade.gui.UIOnClickEvent | None = None,
    ) -> None:
        if self.last_batch_config is None:
            self._open_automated_settings()
            return
        try:
            self.automated_runner.start(self.last_batch_config)
        except RuntimeError as error:
            self._open_automated_settings(message=str(error))
            return
        self.batch_report = None
        self.active_screen = "automated_progress"
        self.manager.clear()
        self.automated_cancel_button = build_automated_progress(
            self.manager,
            on_cancel=self._cancel_automated_batch,
        )

    @staticmethod
    def _open_repository(_event: arcade.gui.UIOnClickEvent | None = None) -> None:
        webbrowser.open(GITHUB_REPOSITORY)
