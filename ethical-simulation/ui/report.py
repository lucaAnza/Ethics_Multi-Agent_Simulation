"""Rendering for the post-simulation analysis report."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import arcade

from ethics.base import DecisionRecord


TEXT = (238, 243, 248)
MUTED = (155, 170, 185)
PANEL = (25, 34, 45, 245)
BORDER = (61, 76, 94)
ACCENT = (42, 177, 230)

CATEGORY_COLORS = {
    "Child": (59, 130, 246),
    "Adult": (249, 115, 22),
    "Elderly": (168, 85, 247),
    "Custom": (34, 197, 94),
}


@dataclass(frozen=True)
class SimulationReportData:
    """UI-independent data needed to render one completed simulation."""

    framework_name: str
    implementation: str
    total_deaths: int
    lane_changes_used: int
    max_lane_changes: int
    casualty_counts: dict[str, int]
    decision_history: list[DecisionRecord]
    framework_metrics: list[tuple[str, str]]


class SimulationReportRenderer:
    """Draw responsive summary cards, charts, and paged decision records."""

    def __init__(self) -> None:
        self._texts: dict[str, arcade.Text] = {}

    @staticmethod
    def items_per_page(height: int) -> int:
        return 2 if height >= 650 else 1

    def page_count(self, data: SimulationReportData, height: int) -> int:
        per_page = self.items_per_page(height)
        return max(1, math.ceil(len(data.decision_history) / per_page))

    def _draw_text(
        self,
        key: str,
        content: str,
        x: float,
        y: float,
        *,
        color=TEXT,
        font_size: int = 10,
        bold: bool = False,
        anchor_x: str = "left",
        anchor_y: str = "center",
        width: float | None = None,
        multiline: bool = False,
    ) -> None:
        cache_key = f"{key}:{font_size}:{bold}:{anchor_x}:{int(width or 0)}"
        text = self._texts.get(cache_key)
        if text is None:
            options: dict[str, Any] = {
                "anchor_x": anchor_x,
                "anchor_y": anchor_y,
                "bold": bold,
            }
            if width is not None:
                options.update(width=width, multiline=multiline)
            text = arcade.Text("", 0, 0, color, font_size, **options)
            self._texts[cache_key] = text
        text.text = content
        text.x = x
        text.y = y
        text.color = color
        text.draw()

    @staticmethod
    def _draw_panel(
        left: float,
        bottom: float,
        width: float,
        height: float,
        *,
        accent=ACCENT,
    ) -> None:
        arcade.draw_lbwh_rectangle_filled(left, bottom, width, height, PANEL)
        arcade.draw_lbwh_rectangle_outline(
            left,
            bottom,
            width,
            height,
            BORDER,
            1,
        )
        arcade.draw_lbwh_rectangle_filled(
            left,
            bottom + height - 3,
            width,
            3,
            accent,
        )

    @staticmethod
    def _specific_metric(
        data: SimulationReportData,
    ) -> tuple[str, str]:
        for label, value in data.framework_metrics:
            if label != "Decisions":
                return label, value
        return "Framework", data.framework_name

    @staticmethod
    def _average_llm_latency(data: SimulationReportData) -> int | None:
        latencies = [
            float(record["latency_ms"])
            for record in data.decision_history
            if isinstance(record.get("latency_ms"), (int, float))
        ]
        if not latencies:
            return None
        return int(round(sum(latencies) / len(latencies)))

    def draw(
        self,
        width: int,
        height: int,
        data: SimulationReportData,
        page: int,
    ) -> None:
        arcade.draw_lbwh_rectangle_filled(0, 0, width, height, (23, 30, 39))
        arcade.draw_lbwh_rectangle_filled(0, height - 4, width, 4, ACCENT)

        self._draw_text(
            "report_title",
            f"SIMULATION REPORT — {data.framework_name.upper()}",
            width / 2,
            height - 34,
            font_size=20,
            bold=True,
            anchor_x="center",
        )
        self._draw_text(
            "report_subtitle",
            (
                "POST-SIMULATION ETHICAL ANALYSIS  ·  IMPLEMENTATION: "
                + (
                    "LLM AGENT"
                    if data.implementation == "llm-agent"
                    else "CODE"
                )
            ),
            width / 2,
            height - 57,
            color=MUTED,
            font_size=9,
            anchor_x="center",
        )

        compact = height < 650
        margin = 36.0
        gap = 14.0
        content_width = width - margin * 2
        summary_height = 60.0 if compact else 76.0
        summary_top = height - 77.0
        summary_bottom = summary_top - summary_height
        metric_label, metric_value = self._specific_metric(data)
        summaries = [
            ("TOTAL DEATHS", str(data.total_deaths), (239, 68, 68)),
            (
                "LANE CHANGES",
                f"{data.lane_changes_used} / {data.max_lane_changes}",
                (249, 166, 35),
            ),
            (
                "DECISIONS",
                str(len(data.decision_history)),
                (59, 130, 246),
            ),
            (metric_label.upper(), metric_value, (34, 197, 94)),
        ]
        average_latency = self._average_llm_latency(data)
        if data.implementation == "llm-agent":
            summaries.append(
                (
                    "AVG LLM TIME",
                    f"{average_latency} ms" if average_latency is not None else "N/A",
                    (168, 85, 247),
                )
            )
        summary_width = (
            content_width - gap * (len(summaries) - 1)
        ) / len(summaries)
        for index, (label, value, accent) in enumerate(summaries):
            left = margin + index * (summary_width + gap)
            self._draw_panel(
                left,
                summary_bottom,
                summary_width,
                summary_height,
                accent=accent,
            )
            self._draw_text(
                f"summary_label_{index}",
                label,
                left + 14,
                summary_top - 21,
                color=MUTED,
                font_size=8,
                bold=True,
            )
            self._draw_text(
                f"summary_value_{index}",
                value,
                left + 14,
                summary_bottom + (18 if compact else 25),
                font_size=17 if compact else 21,
                bold=True,
            )

        charts_top = summary_bottom - 14.0
        charts_height = 110.0 if compact else 190.0
        charts_bottom = charts_top - charts_height
        histogram_width = content_width * 0.59
        pie_left = margin + histogram_width + gap
        pie_width = content_width - histogram_width - gap
        self._draw_histogram(
            margin,
            charts_bottom,
            histogram_width,
            charts_height,
            data.casualty_counts,
            compact,
        )
        self._draw_lane_change_pie(
            pie_left,
            charts_bottom,
            pie_width,
            charts_height,
            data.lane_changes_used,
            data.max_lane_changes,
            compact,
        )

        history_heading_y = charts_bottom - 25.0
        self._draw_text(
            "history_heading",
            "DECISION HISTORY",
            margin,
            history_heading_y,
            font_size=13,
            bold=True,
        )
        page_count = self.page_count(data, height)
        self._draw_text(
            "history_page",
            f"PAGE {page + 1} / {page_count}",
            width - margin,
            history_heading_y,
            color=MUTED,
            font_size=8,
            anchor_x="right",
        )

        history_top = history_heading_y - 22.0
        history_bottom = 64.0 if compact else 78.0
        self._draw_history(
            margin,
            history_bottom,
            content_width,
            max(60.0, history_top - history_bottom),
            data,
            page,
            compact,
        )

    def _draw_histogram(
        self,
        left: float,
        bottom: float,
        width: float,
        height: float,
        counts: dict[str, int],
        compact: bool,
    ) -> None:
        self._draw_panel(left, bottom, width, height)
        self._draw_text(
            "histogram_title",
            "DEATHS BY CATEGORY",
            left + 14,
            bottom + height - 20,
            font_size=10,
            bold=True,
        )
        categories = list(counts) or ["None"]
        values = [counts.get(category, 0) for category in categories]
        maximum = max(1, *values)
        chart_left = left + 34
        chart_right = left + width - 20
        chart_bottom = bottom + (25 if compact else 32)
        chart_top = bottom + height - (35 if compact else 42)
        arcade.draw_line(
            chart_left,
            chart_bottom,
            chart_right,
            chart_bottom,
            (80, 94, 110),
            1,
        )
        slot_width = (chart_right - chart_left) / len(categories)
        bar_width = min(56.0, slot_width * 0.52)
        for index, (category, value) in enumerate(zip(categories, values)):
            center_x = chart_left + slot_width * (index + 0.5)
            bar_height = (
                (chart_top - chart_bottom) * value / maximum if value else 2.0
            )
            color = CATEGORY_COLORS.get(category, (100, 116, 139))
            arcade.draw_lbwh_rectangle_filled(
                center_x - bar_width / 2,
                chart_bottom,
                bar_width,
                bar_height,
                color,
            )
            self._draw_text(
                f"hist_value_{index}",
                str(value),
                center_x,
                chart_bottom + bar_height + 10,
                font_size=8,
                bold=True,
                anchor_x="center",
            )
            self._draw_text(
                f"hist_label_{index}",
                category.upper(),
                center_x,
                bottom + 11,
                color=MUTED,
                font_size=7,
                anchor_x="center",
            )

    def _draw_lane_change_pie(
        self,
        left: float,
        bottom: float,
        width: float,
        height: float,
        used: int,
        maximum: int,
        compact: bool,
    ) -> None:
        self._draw_panel(left, bottom, width, height, accent=(249, 166, 35))
        self._draw_text(
            "pie_title",
            "LANE CHANGE USAGE",
            left + 14,
            bottom + height - 20,
            font_size=10,
            bold=True,
        )
        remaining = max(0, maximum - used)
        total = used + remaining
        diameter = min(width * 0.34, height - (50 if compact else 55))
        center_x = left + width * 0.32
        center_y = bottom + height * 0.46
        if total == 0:
            arcade.draw_circle_filled(
                center_x,
                center_y,
                diameter / 2,
                (71, 85, 105),
            )
        else:
            used_angle = 360.0 * used / total
            arcade.draw_arc_filled(
                center_x,
                center_y,
                diameter,
                diameter,
                (71, 85, 105),
                0,
                360,
            )
            if used_angle:
                arcade.draw_arc_filled(
                    center_x,
                    center_y,
                    diameter,
                    diameter,
                    (249, 166, 35),
                    90,
                    90 + used_angle,
                )

        legend_x = left + width * 0.58
        for index, (label, value, color) in enumerate(
            (
                ("Used", used, (249, 166, 35)),
                ("Remaining", remaining, (100, 116, 139)),
            )
        ):
            legend_y = center_y + 15 - index * 31
            arcade.draw_circle_filled(legend_x, legend_y, 5, color)
            self._draw_text(
                f"pie_legend_{index}",
                f"{label}: {value}",
                legend_x + 12,
                legend_y,
                font_size=8 if compact else 9,
            )

    @staticmethod
    def _decision_detail(record: DecisionRecord) -> str:
        details = record.get("framework_details", {})
        if details.get("lane_change_blocked"):
            return "Lane change unavailable: maximum reached"
        if record.get("mode") == "llm-agent":
            suffix = " · FALLBACK" if record.get("fallback") else ""
            return (
                f"LLM: {record.get('model', 'Unknown')} · "
                f"{record.get('latency_ms', '?')} ms{suffix}"
            )
        if details.get("deciding_rule"):
            return f"Rule: {details['deciding_rule']}"
        if details.get("moral_conflict"):
            return f"Conflict resolver: {details.get('conflict_resolver', 'Unknown')}"
        if details.get("rule_outcome"):
            return f"Rule outcome: {details['rule_outcome']}"
        return ""

    def _draw_history(
        self,
        left: float,
        bottom: float,
        width: float,
        height: float,
        data: SimulationReportData,
        page: int,
        compact: bool,
    ) -> None:
        per_page = self.items_per_page(500 if compact else 800)
        first = page * per_page
        records = data.decision_history[first : first + per_page]
        if not records:
            self._draw_panel(left, bottom, width, height, accent=(100, 116, 139))
            self._draw_text(
                "history_empty",
                "No ethical decisions were required during this simulation.",
                left + width / 2,
                bottom + height / 2,
                color=MUTED,
                font_size=11,
                anchor_x="center",
            )
            return

        gap = 14.0
        card_width = (width - gap * (len(records) - 1)) / len(records)
        for index, record in enumerate(records):
            card_left = left + index * (card_width + gap)
            accent = (
                (249, 166, 35)
                if record.get("action") == "CHANGE_LANE"
                else (34, 197, 94)
            )
            self._draw_panel(
                card_left,
                bottom,
                card_width,
                height,
                accent=accent,
            )
            text_left = card_left + 14
            top = bottom + height
            line_step = 17 if compact else 21
            self._draw_text(
                f"history_{index}_title",
                (
                    f"DECISION #{record.get('decision_id', '?')}  —  "
                    f"x = {record.get('position_x', '?')} px"
                ),
                text_left,
                top - 20,
                font_size=10,
                bold=True,
            )
            rows = (
                f"Current lane: {record.get('current_lane_situation', '-')}",
                f"Other lane: {record.get('other_lane_situation', '-')}",
                f"Action: {record.get('action', '-')}",
            )
            for row_index, row in enumerate(rows):
                self._draw_text(
                    f"history_{index}_row_{row_index}",
                    row,
                    text_left,
                    top - 20 - (row_index + 1) * line_step,
                    font_size=8 if compact else 9,
                    bold=row_index == 2,
                )

            detail = self._decision_detail(record)
            if detail:
                detail_color = (
                    (248, 113, 113)
                    if record.get("framework_details", {}).get(
                        "lane_change_blocked"
                    )
                    else (96, 165, 250)
                )
                self._draw_text(
                    f"history_{index}_framework",
                    detail,
                    text_left,
                    top - 20 - 4 * line_step,
                    color=detail_color,
                    font_size=8,
                    bold=True,
                )
            reason_y = top - 20 - (5 if detail else 4) * line_step
            self._draw_text(
                f"history_{index}_reason",
                f"Reason: {record.get('reason', '-')}",
                text_left,
                reason_y,
                color=MUTED,
                font_size=8 if compact else 9,
                anchor_y="top",
                width=card_width - 28,
                multiline=True,
            )
