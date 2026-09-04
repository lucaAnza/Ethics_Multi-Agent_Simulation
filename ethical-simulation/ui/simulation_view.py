"""Drawing helpers for the interactive simulation overlays and HUD."""

from __future__ import annotations

import arcade

from decision_engine import LLM_MODE
from ethics.base import CHANGE_LANE
from simulation.config import (
    MAX_CONFIGURABLE_VEHICLE_SPEED_KMH,
    TOP_TOOLBAR_HEIGHT as TOOLBAR_HEIGHT,
)
from simulation.entities import Pedestrian


class SimulationViewMixin:
    """Render simulation-only overlays while keeping the world independent."""

    @staticmethod
    def _create_hud_texts() -> dict[str, arcade.Text]:
        def text(
            font_size: int,
            *,
            anchor_x: str = "left",
            bold: bool = False,
        ) -> arcade.Text:
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
            "lane": text(10, bold=True),
            "changes": text(10),
            "vision": text(9),
            "decision": text(9),
            "last_action": text(9, bold=True),
        }

    def _set_hud_text(self, name: str, content: str, x: float, y: float) -> None:
        text = self._hud_texts[name]
        text.text = content
        text.x = x
        text.y = y
        text.draw()

    @staticmethod
    def _create_perception_texts() -> dict[str, arcade.Text]:
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
            texts[f"detail_{index}"] = arcade.Text(
                "",
                0,
                0,
                (210, 218, 226),
                10,
                anchor_y="center",
            )
        return texts

    @staticmethod
    def _create_llm_loading_texts() -> dict[str, arcade.Text]:
        return {
            "title": arcade.Text(
                "ANALYZING ETHICAL DILEMMA...",
                0,
                0,
                (255, 237, 170),
                14,
                anchor_x="center",
                anchor_y="center",
                bold=True,
            ),
            "subtitle": arcade.Text(
                "",
                0,
                0,
                (203, 213, 225),
                9,
                anchor_x="center",
                anchor_y="center",
            ),
        }

    def _draw_llm_loading_overlay(self) -> None:
        panel_width = 430.0
        panel_height = 96.0
        left = (self.width - panel_width) / 2
        bottom = (self.height - panel_height) / 2
        arcade.draw_lbwh_rectangle_filled(
            left,
            bottom,
            panel_width,
            panel_height,
            (24, 32, 42, 242),
        )
        arcade.draw_lbwh_rectangle_outline(
            left,
            bottom,
            panel_width,
            panel_height,
            (249, 166, 35),
            2,
        )
        title = self._llm_loading_texts["title"]
        title.x, title.y = self.width / 2, bottom + 60
        title.draw()
        subtitle = self._llm_loading_texts["subtitle"]
        subtitle.text = (
            f"{self.current_framework} · {self.llm_decision_engine.model_name} "
            "· simulation time paused"
        )
        subtitle.x, subtitle.y = self.width / 2, bottom + 31
        subtitle.draw()

    def _draw_simulation_end_overlay(self) -> None:
        dead = self.world.dead_pedestrians()
        panel_width = 520
        panel_height = 350
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
            status.text = f"Tunnel reached · Victims: {len(dead)}"
            status.color = (238, 68, 68)
        else:
            status.text = "Tunnel reached · Success nobody is dead!"
            status.color = (79, 196, 123)
        status.x, status.y = center_x, panel_top - 72
        status.draw()

        category_counts = self._casualty_category_counts(dead)

        summary_lines = [
            (
                f"Lane changes: {self.world.lane_changes_used} / "
                f"{self.world.max_spostamenti}"
            ),
            f"Child: {category_counts['Child']}",
            f"Adult: {category_counts['Adult']}",
            f"Elderly: {category_counts['Elderly']}",
        ]
        summary_lines.append(f"Framework: {self.current_framework}")
        summary_lines.append(
            "Implementation: "
            + (
                "LLM Agent"
                if self.current_implementation == LLM_MODE
                else "Code"
            )
        )

        framework = self.ethical_frameworks.get(self.current_framework)
        casualties = [
            {"model": person.model, "label": person.label}
            for person in dead
        ]
        if framework is not None:
            summary_lines.extend(
                f"{label}: {value}"
                for label, value in framework.summary(casualties)
            )

        for index, line in enumerate(summary_lines):
            detail = self._end_texts[f"detail_{index}"]
            detail.text = line
            detail.x = panel_left + 58
            detail.y = panel_top - 108 - index * 22
            detail.draw()

        hint = self._end_texts["hint"]
        hint.text = "Open the report or reset to start a new simulation."
        hint.x, hint.y = center_x, panel_bottom + 24
        hint.draw()

    def _set_perception_text(
        self,
        name: str,
        content: str,
        x: float,
        y: float,
        color: tuple[int, int, int] | None = None,
    ) -> None:
        text = self._perception_texts[name]
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
        }
        counts: dict[str, int] = {}
        for pedestrian in casualties:
            label = labels[pedestrian.model]
            counts[label] = counts.get(label, 0) + 1

        if not counts:
            return ["No visible entities"]
        return [f"{label}: {count}" for label, count in counts.items()]

    def _draw_vehicle_perception(self) -> None:
        current_entities, other_entities = self.world.visible_lane_entities()
        incident_distance = self.world.next_incident_distance()
        panel_left = 14
        panel_width = 300
        panel_height = 250
        panel_top = self.height - TOOLBAR_HEIGHT - 14
        panel_bottom = panel_top - panel_height
        content_left = panel_left + 16
        decision_due = (
            incident_distance is not None
            and incident_distance <= self.world.decision_distance
        )
        accent = (238, 68, 68) if decision_due else (42, 177, 230)

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
        arcade.draw_lbwh_rectangle_filled(
            panel_left,
            panel_top - 4,
            panel_width,
            4,
            accent,
        )
        self._set_perception_text(
            "title",
            "VEHICLE PERCEPTION",
            content_left,
            panel_top - 26,
        )
        self._set_perception_text(
            "subtitle",
            (
                f"VISION {self.world.vision_distance:.0f}px  ·  "
                f"DECISION {self.world.decision_distance:.0f}px"
            ),
            content_left,
            panel_top - 43,
        )
        card_top = panel_top - 58
        card_bottom = panel_bottom + 15
        card_color = (69, 30, 35, 235) if decision_due else (25, 43, 55, 235)
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
        if incident_distance is None:
            status = "CURRENT LANE CLEAR"
        elif decision_due:
            status = f"DECISION ZONE · {incident_distance:.0f}px"
        else:
            status = f"TRACKING INCIDENT · {incident_distance:.0f}px"
        self._set_perception_text(
            "status",
            status,
            content_left + 13,
            card_top - 25,
            accent,
        )

        details = [f"Current lane: {len(current_entities)}"]
        details.extend(
            f"  {line}" for line in self._demographic_lines(current_entities)
        )
        details.append(f"Adjacent lane: {len(other_entities)}")
        details.extend(f"  {line}" for line in self._demographic_lines(other_entities))
        for index, detail in enumerate(details[:7]):
            self._set_perception_text(
                f"detail_{index}",
                detail,
                content_left + 13,
                card_top - 51 - index * 18,
                (210, 218, 226),
            )

    def _draw_vehicle_hud(self) -> None:
        car = self.world.cars[0]
        speed_kmh = car.speed

        panel_width = 278
        panel_height = 258
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
        arcade.draw_lbwh_rectangle_filled(
            panel_left,
            panel_top - 4,
            panel_width,
            4,
            (42, 177, 230),
        )

        self._set_hud_text("title", "VEHICLE STATUS", content_left, panel_top - 25)
        self._set_hud_text(
            "speed",
            f"{speed_kmh:04.1f}",
            content_right - 47,
            panel_top - 65,
        )
        self._set_hud_text("unit", "km/h", content_right - 39, panel_top - 65)

        speed_bar_y = panel_top - 93
        speed_bar_width = panel_width - 36
        speed_ratio = min(speed_kmh / MAX_CONFIGURABLE_VEHICLE_SPEED_KMH, 1.0)
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

        lane_name = "UPPER" if car.lane_index == 1 else "LOWER"
        target_lane_name = "LOWER" if car.lane_index == 1 else "UPPER"
        lane_status = (
            f"LANE  CHANGING TO {target_lane_name}"
            if car.is_changing_lane
            else f"LANE  {lane_name}"
        )
        self._set_hud_text("lane", lane_status, content_left, panel_top - 119)
        self._set_hud_text(
            "changes",
            (
                f"LANE CHANGES  {self.world.lane_changes_used} / "
                f"{self.world.max_spostamenti}"
            ),
            content_left,
            panel_top - 145,
        )
        self._set_hud_text(
            "vision",
            f"VISION DISTANCE  {self.world.vision_distance:.0f} px",
            content_left,
            panel_top - 171,
        )
        self._set_hud_text(
            "decision",
            f"DECISION DISTANCE  {self.world.decision_distance:.0f} px",
            content_left,
            panel_top - 195,
        )
        last_action = self.last_decision.action if self.last_decision else "WAITING"
        action_color = (
            (245, 170, 55)
            if last_action == CHANGE_LANE
            else (79, 196, 123)
        )
        self._hud_texts["last_action"].color = action_color
        self._set_hud_text(
            "last_action",
            f"LAST DECISION  {last_action}",
            content_left,
            panel_top - 226,
        )
