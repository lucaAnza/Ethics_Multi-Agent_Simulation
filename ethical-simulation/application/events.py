"""Arcade update, draw, keyboard, and pointer event handlers."""

from __future__ import annotations

import arcade

from decision_engine import WAITING_FOR_LLM
from simulation.config import LANE_OFFSET, TOP_TOOLBAR_HEIGHT as TOOLBAR_HEIGHT
from ui.screens import build_batch_report_navigation


class WindowEventsMixin:
    """Dispatch window events according to the active application screen."""

    def on_update(self, delta_time: float) -> None:
        if self.active_screen == "automated_progress":
            report = self.automated_runner.poll_report()
            if report is not None:
                self.batch_report = report
                self.active_screen = "batch_report"
                self.manager.clear()
                build_batch_report_navigation(
                    self.manager,
                    on_back=self._open_automated_settings,
                    on_restart=self._restart_automated_batch,
                )
            return

        if self.active_screen != "simulation":
            return

        if not self.is_running:
            return

        scaled_delta_time = delta_time * self.time_scale
        step = self.simulation_engine.step(scaled_delta_time)
        self._sync_simulation_engine_state()
        if step.decision_event is not None:
            self._log_simulation_decision(step.decision_event)
        if step.reached_tunnel and not self.simulation_finished:
            self._show_simulation_end()

    def on_draw(self) -> None:
        self.clear()
        if self.active_screen == "scenario_location_picker":
            if self.scenario_location_preview is not None:
                self.scenario_location_preview.draw(show_vehicle_vision=False)
            cursor_x, cursor_y = self.scenario_location_cursor
            if cursor_y < self.height - TOOLBAR_HEIGHT - 6:
                entity_kind, _entity_index = self.scenario_editor_entity
                entity_top_offset = 34 if entity_kind == "cars" else 22
                arrow_tip_y = cursor_y + entity_top_offset
                arrow_base_y = arrow_tip_y + 12
                marker_color = (190, 145, 25)
                arcade.draw_line(
                    cursor_x,
                    arrow_base_y + 22,
                    cursor_x,
                    arrow_base_y,
                    marker_color,
                    3,
                )
                arcade.draw_triangle_filled(
                    cursor_x - 7,
                    arrow_base_y,
                    cursor_x + 7,
                    arrow_base_y,
                    cursor_x,
                    arrow_tip_y,
                    marker_color,
                )
                self.scenario_location_text.x = cursor_x
                self.scenario_location_text.y = arrow_base_y + 27
                self.scenario_location_text.draw()
                arcade.draw_circle_outline(
                    cursor_x,
                    cursor_y,
                    15,
                    (42, 177, 230),
                    2,
                    num_segments=32,
                )
                arcade.draw_line(
                    cursor_x - 21,
                    cursor_y,
                    cursor_x + 21,
                    cursor_y,
                    (42, 177, 230),
                    2,
                )
                arcade.draw_line(
                    cursor_x,
                    cursor_y - 21,
                    cursor_x,
                    cursor_y + 21,
                    (42, 177, 230),
                    2,
                )
            self.manager.draw()
            return
        if self.active_screen == "report":
            self.report_renderer.draw(
                self.width,
                self.height,
                self._build_report_data(),
                self.report_page,
            )
            self.manager.draw()
            return
        if self.active_screen == "automated_progress":
            self.batch_renderer.draw_progress(
                self.width,
                self.height,
                self.automated_runner.progress(),
            )
            self.manager.draw()
            return
        if self.active_screen == "batch_report" and self.batch_report is not None:
            self.batch_renderer.draw_report(
                self.width,
                self.height,
                self.batch_report,
            )
            self.manager.draw()
            return
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
        self._draw_vehicle_perception()
        self._draw_vehicle_hud()
        if self.decision_phase == WAITING_FOR_LLM:
            self._draw_llm_loading_overlay()
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
                if self.active_screen == "scenario_location_picker":
                    self._cancel_scenario_location_picker()
                elif self.active_screen == "report":
                    self._back_to_summary()
                elif self.active_screen == "automated_progress":
                    self._cancel_automated_batch()
                elif self.active_screen == "batch_report":
                    self._open_automated_settings()
                elif self.active_screen == "automated_settings":
                    self._return_to_simulation()
                elif self.active_screen == "menu":
                    self._return_to_simulation()
                else:
                    self._open_menu()

    def on_mouse_motion(
        self,
        x: int,
        y: int,
        dx: int,
        dy: int,
    ) -> None:
        if self.active_screen == "scenario_location_picker":
            entity_kind, entity_index = self.scenario_editor_entity
            bounded_x, bounded_y = self._bounded_scenario_location(
                x,
                y,
                entity_kind,
            )
            self.scenario_location_cursor = (bounded_x, bounded_y)
            if self.scenario_location_preview is not None:
                preview_entities = (
                    self.scenario_location_preview.cars
                    if entity_kind == "cars"
                    else self.scenario_location_preview.pedestrians
                )
                preview_entities[entity_index].x = bounded_x
                preview_entities[entity_index].y = bounded_y
                if entity_kind == "cars":
                    preview_entities[entity_index].lane_index = (
                        1 if bounded_y > self.world.road_y else 0
                    )

    def on_mouse_press(
        self,
        x: int,
        y: int,
        button: int,
        modifiers: int,
    ) -> None:
        if (
            self.active_screen != "scenario_location_picker"
            or button != arcade.MOUSE_BUTTON_LEFT
            or y >= self.height - TOOLBAR_HEIGHT - 6
        ):
            return

        entity_kind, entity_index = self.scenario_editor_entity
        bounded_x, bounded_y = self._bounded_scenario_location(
            x,
            y,
            entity_kind,
        )
        entity = self.scenario_editor_draft[self.scenario_editor_scenario][entity_kind][
            entity_index
        ]
        entity["x"] = bounded_x
        if entity_kind == "cars":
            entity["y_offset"] = (
                LANE_OFFSET if bounded_y > self.world.road_y else -LANE_OFFSET
            )
        else:
            entity["y_offset"] = bounded_y - self.world.road_y
        self.scenario_editor_message = (
            f"Location set to X {bounded_x:.0f}, Y {bounded_y:.0f}. "
            "Save to make it persistent."
        )
        self.scenario_location_preview = None
        self._show_scenario_editor()

    def _bounded_scenario_location(
        self,
        x: int,
        y: int,
        entity_kind: str,
    ) -> tuple[float, float]:
        """Constrain a location-picker coordinate to valid entity bounds."""
        margin = 40.0 if entity_kind == "cars" else 12.0
        bounded_x = min(max(float(x), margin), self.width - margin)
        if entity_kind == "cars":
            bounded_y = min(
                self.world.lane_centers,
                key=lambda lane_y: abs(y - lane_y),
            )
        else:
            bounded_y = min(max(float(y), margin), self.height - 84.0)
        return bounded_x, bounded_y
