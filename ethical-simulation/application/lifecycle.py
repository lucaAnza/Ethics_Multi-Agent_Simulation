"""Simulation lifecycle, final summary, and report navigation."""

from __future__ import annotations

from copy import deepcopy

import arcade
import arcade.gui

from app_logging import application_logger
from decision_engine import DRIVING
from ethics.base import CHANGE_LANE
from ethics.utils.config import CONSTANT, UTILITARIANISM
from simulation import SimulationDecisionEvent
from simulation.entities import Pedestrian
from simulation.statistics import casualty_category_counts, casualty_entity_counts
from ui.report import SimulationReportData
from ui.screens import build_report_navigation
from ui.theme import REPORT_BUTTON_STYLE


class SimulationLifecycleMixin:
    """Coordinate run state without owning simulation-domain behavior."""

    def _configure_simulation_engine(self) -> None:
        if not hasattr(self, "simulation_engine"):
            return
        self.simulation_engine.configure(
            framework_name=self.current_framework,
            implementation=self.current_implementation,
            framework=self.ethical_frameworks[self.current_framework],
        )
        self._sync_simulation_engine_state()

    def _sync_simulation_engine_state(self) -> None:
        self.decision_phase = self.simulation_engine.phase
        self.decision_sequence = self.simulation_engine.decision_sequence
        self.last_decision = self.simulation_engine.last_decision

    @staticmethod
    def _log_simulation_decision(event: SimulationDecisionEvent) -> None:
        application_logger.log_decision(
            framework=event.framework_name,
            implementation=event.implementation,
            model=event.applied_decision.details.get("model"),
            current_lane_count=len(event.context.current_lane_entities),
            other_lane_count=len(event.context.other_lane_entities),
            framework_action=event.recommended_decision.action,
            applied_action=event.applied_decision.action,
            reason=event.applied_decision.reason,
            lane_change_blocked=(
                event.recommended_decision.action == CHANGE_LANE
                and not event.lane_change_started
            ),
            llm_request=event.llm_request,
            llm_response=event.llm_response,
            llm_raw_response=event.llm_raw_response,
            latency_ms=event.applied_decision.details.get("latency_ms"),
            attempts=event.applied_decision.details.get("attempts"),
        )

    def _framework_configuration(self, framework_name: str) -> dict:
        """Return an isolated configuration for one ethical framework."""
        if framework_name == UTILITARIANISM:
            return {
                "entity_values": deepcopy(
                    self.framework_settings[UTILITARIANISM]
                )
            }
        settings = deepcopy(self.framework_settings.get(framework_name, {}))
        if framework_name == CONSTANT:
            settings["entity_values"] = deepcopy(
                self.framework_settings[UTILITARIANISM]
            )
        return settings

    def _cancel_pending_decision(self) -> None:
        if hasattr(self, "simulation_engine"):
            self.simulation_engine.cancel_pending_decision()
            self._sync_simulation_engine_state()
        elif hasattr(self, "llm_decision_engine"):
            self.llm_decision_engine.cancel()

    def _stop(self, _event: arcade.gui.UIOnClickEvent) -> None:
        self.world.reset()
        self._apply_current_scenario_vehicle_settings()
        self._sync_vehicle_control_values()
        self._reset_run_state()

    def _show_simulation_end(self) -> None:
        self.is_running = False
        self.simulation_finished = True
        self.decision_phase = DRIVING
        self.manager.clear()
        self._setup_simulation_end_actions()

    def _setup_simulation_end_actions(self) -> None:
        panel_height = 350
        report_button = arcade.gui.UIFlatButton(
            text="Report",
            width=160,
            height=42,
            style=REPORT_BUTTON_STYLE,
        )
        report_button.on_click = self._open_report
        reset_button = arcade.gui.UIFlatButton(
            text="Reset",
            width=160,
            height=42,
            style=arcade.gui.UIFlatButton.STYLE_BLUE,
        )
        reset_button.on_click = self._reset_from_end
        anchor = arcade.gui.UIAnchorLayout()
        anchor.add(
            report_button,
            anchor_x="center",
            anchor_y="center",
            align_x=-88,
            align_y=-panel_height / 2 + 54,
        )
        anchor.add(
            reset_button,
            anchor_x="center",
            anchor_y="center",
            align_x=88,
            align_y=-panel_height / 2 + 54,
        )
        self.manager.add(anchor)

    def _reset_from_end(self, event: arcade.gui.UIOnClickEvent) -> None:
        self.active_screen = "simulation"
        self._stop(event)
        self.manager.clear()
        self._setup_toolbar()

    @staticmethod
    def _casualty_category_counts(
        dead: list[Pedestrian],
    ) -> dict[str, int]:
        return casualty_category_counts(dead)

    def _build_report_data(self) -> SimulationReportData:
        dead = self.world.dead_pedestrians()
        casualties = [
            {"model": person.model, "label": person.label}
            for person in dead
        ]
        framework = self.ethical_frameworks.get(self.current_framework)
        history = list(framework.decision_history) if framework is not None else []
        metrics = framework.summary(casualties) if framework is not None else []
        return SimulationReportData(
            framework_name=self.current_framework,
            implementation=self.current_implementation,
            total_deaths=len(dead),
            lane_changes_used=self.world.lane_changes_used,
            max_lane_changes=self.world.max_spostamenti,
            casualty_counts=self._casualty_category_counts(dead),
            casualty_entity_counts=casualty_entity_counts(dead),
            decision_history=history,
            framework_metrics=metrics,
        )

    def _open_report(
        self,
        _event: arcade.gui.UIOnClickEvent | None = None,
    ) -> None:
        if not self.simulation_finished:
            return
        self.active_screen = "report"
        self.report_page = 0
        self._setup_report_navigation()

    def _setup_report_navigation(self) -> None:
        data = self._build_report_data()
        page_count = self.report_renderer.page_count(data, self.height)
        self.report_page = max(0, min(self.report_page, page_count - 1))
        self.manager.clear()
        build_report_navigation(
            self.manager,
            page=self.report_page,
            page_count=page_count,
            on_previous=self._previous_report_page,
            on_next=self._next_report_page,
            on_back=self._back_to_summary,
            on_restart=self._reset_from_end,
        )

    def _previous_report_page(
        self,
        _event: arcade.gui.UIOnClickEvent | None = None,
    ) -> None:
        self.report_page = max(0, self.report_page - 1)
        self._setup_report_navigation()

    def _next_report_page(
        self,
        _event: arcade.gui.UIOnClickEvent | None = None,
    ) -> None:
        page_count = self.report_renderer.page_count(
            self._build_report_data(),
            self.height,
        )
        self.report_page = min(page_count - 1, self.report_page + 1)
        self._setup_report_navigation()

    def _back_to_summary(
        self,
        _event: arcade.gui.UIOnClickEvent | None = None,
    ) -> None:
        self.active_screen = "simulation"
        self.manager.clear()
        self._setup_simulation_end_actions()
