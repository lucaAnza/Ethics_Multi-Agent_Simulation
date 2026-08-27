"""Arcade rendering for automated-simulation progress and aggregate reports."""

from __future__ import annotations

from typing import Any

import arcade

from automated import (
    COMPARISON,
    BatchProgress,
    BatchReport,
    ImplementationMetrics,
)
from decision_engine.modes import CODE_MODE, LLM_MODE
from ethics.base import CHANGE_LANE, STAY
from simulation.entities import PEDESTRIAN_MODEL_COLORS, PEDESTRIAN_MODEL_LABELS
from ui.theme import BORDER, MUTED, PANEL, TEXT


ACCENT = (14, 165, 233)
CATEGORY_COLORS = {
    "Child": (59, 130, 246),
    "Adult": (249, 115, 22),
    "Elderly": (168, 85, 247),
}
CODE_COLOR = (59, 130, 246)
LLM_COLOR = (249, 146, 60)


def _format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "Calculating..."
    total = max(0, int(round(seconds)))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


class BatchReportRenderer:
    """Draw progress and a compact aggregate report without UI state."""

    def __init__(self) -> None:
        self._texts: dict[str, arcade.Text] = {}

    def _text(
        self,
        key: str,
        value: str,
        x: float,
        y: float,
        *,
        color=TEXT,
        size: int = 10,
        bold: bool = False,
        anchor_x: str = "left",
    ) -> None:
        cache_key = f"{key}:{size}:{bold}:{anchor_x}"
        text = self._texts.get(cache_key)
        if text is None:
            text = arcade.Text(
                "",
                0,
                0,
                color,
                size,
                bold=bold,
                anchor_x=anchor_x,
                anchor_y="center",
            )
            self._texts[cache_key] = text
        text.text = value
        text.x = x
        text.y = y
        text.color = color
        text.draw()

    @staticmethod
    def _background(width: int, height: int) -> None:
        arcade.draw_lbwh_rectangle_filled(0, 0, width, height, (23, 30, 39))
        arcade.draw_lbwh_rectangle_filled(0, height - 4, width, 4, ACCENT)

    @staticmethod
    def _panel(
        left: float,
        bottom: float,
        width: float,
        height: float,
        accent=ACCENT,
    ) -> None:
        arcade.draw_lbwh_rectangle_filled(left, bottom, width, height, PANEL)
        arcade.draw_lbwh_rectangle_outline(left, bottom, width, height, BORDER, 1)
        arcade.draw_lbwh_rectangle_filled(
            left,
            bottom + height - 3,
            width,
            3,
            accent,
        )

    def draw_progress(
        self,
        width: int,
        height: int,
        progress: BatchProgress,
    ) -> None:
        self._background(width, height)
        panel_width = min(720.0, width - 100.0)
        panel_height = 390.0
        left = (width - panel_width) / 2
        bottom = (height - panel_height) / 2
        self._panel(left, bottom, panel_width, panel_height)
        center_x = width / 2
        self._text(
            "progress_title",
            "AUTOMATED SIMULATION",
            center_x,
            bottom + panel_height - 48,
            size=22,
            bold=True,
            anchor_x="center",
        )
        self._text(
            "progress_mode",
            f"MODE  ·  {progress.mode.upper()}",
            center_x,
            bottom + panel_height - 78,
            color=MUTED,
            size=9,
            anchor_x="center",
        )
        self._text(
            "progress_count",
            f"Progress: {progress.completed_units} / {progress.total_units}",
            left + 54,
            bottom + 238,
            size=13,
            bold=True,
        )
        percent = int(round(progress.fraction * 100))
        bar_left = left + 54
        bar_bottom = bottom + 198
        bar_width = panel_width - 108
        arcade.draw_lbwh_rectangle_filled(
            bar_left,
            bar_bottom,
            bar_width,
            22,
            (51, 65, 85),
        )
        if progress.fraction:
            arcade.draw_lbwh_rectangle_filled(
                bar_left,
                bar_bottom,
                bar_width * progress.fraction,
                22,
                (37, 99, 235),
            )
        self._text(
            "progress_percent",
            f"{percent}%",
            center_x,
            bar_bottom + 11,
            size=9,
            bold=True,
            anchor_x="center",
        )
        self._text(
            "progress_run",
            progress.current_run,
            left + 54,
            bottom + 166,
            color=(125, 211, 252),
            size=10,
        )
        self._text(
            "progress_decisions",
            f"Decisions completed: {progress.decisions_completed}",
            left + 54,
            bottom + 138,
            color=MUTED,
            size=10,
        )
        if progress.waiting_for_llm:
            self._text(
                "progress_waiting",
                "Waiting for LLM...",
                left + panel_width - 54,
                bottom + 138,
                color=(251, 146, 60),
                size=10,
                bold=True,
                anchor_x="right",
            )
        self._text(
            "progress_elapsed",
            f"Elapsed time: {_format_duration(progress.elapsed_seconds)}",
            left + 54,
            bottom + 104,
            size=10,
        )
        self._text(
            "progress_eta",
            "Estimated remaining: "
            + _format_duration(progress.estimated_remaining_seconds),
            left + panel_width - 54,
            bottom + 104,
            size=10,
            anchor_x="right",
        )
        if progress.error:
            self._text(
                "progress_error",
                progress.error[:100],
                center_x,
                bottom + 72,
                color=(248, 113, 113),
                size=9,
                anchor_x="center",
            )

    def draw_report(self, width: int, height: int, report: BatchReport) -> None:
        self._background(width, height)
        margin = 38.0
        content_width = width - margin * 2
        self._text(
            "batch_title",
            "BATCH REPORT",
            width / 2,
            height - 34,
            size=21,
            bold=True,
            anchor_x="center",
        )
        state = (
            "CANCELLED · PARTIAL RESULTS"
            if report.cancelled
            else report.mode.upper()
        )
        self._text(
            "batch_subtitle",
            state,
            width / 2,
            height - 59,
            color=(251, 146, 60) if report.cancelled else MUTED,
            size=9,
            anchor_x="center",
        )

        if report.mode == COMPARISON:
            self._draw_comparison_report(width, height, report, margin, content_width)
        else:
            self._draw_single_report(width, height, report, margin, content_width)

    def _draw_cards(
        self,
        left: float,
        bottom: float,
        width: float,
        cards: list[tuple[str, str, tuple[int, int, int]]],
    ) -> None:
        gap = 12.0
        card_width = (width - gap * (len(cards) - 1)) / len(cards)
        label_size = 7 if len(cards) > 5 else 8
        value_size = 12 if len(cards) > 7 else 14 if len(cards) > 5 else 17
        for index, (label, value, color) in enumerate(cards):
            card_left = left + index * (card_width + gap)
            self._panel(card_left, bottom, card_width, 68, color)
            self._text(
                f"batch_card_label_{index}",
                label,
                card_left + 10,
                bottom + 45,
                color=MUTED,
                size=label_size,
                bold=True,
            )
            self._text(
                f"batch_card_value_{index}",
                value,
                card_left + 10,
                bottom + 21,
                size=value_size,
                bold=True,
            )

    def _draw_single_report(
        self,
        width: int,
        height: int,
        report: BatchReport,
        margin: float,
        content_width: float,
    ) -> None:
        metrics = report.primary_metrics
        gap = 12.0
        stay_count = metrics.action_counts[STAY]
        change_count = metrics.action_counts[CHANGE_LANE]
        cards = [
            ("SIMULATIONS", str(metrics.simulation_count), CODE_COLOR),
            ("TOTAL CASUALTIES", str(metrics.total_casualties), (239, 68, 68)),
            ("AVG CASUALTIES", f"{metrics.average_casualties:.2f}", (244, 114, 92)),
            ("ZERO-CASUALTY", f"{metrics.zero_casualty_rate:.1f}%", (34, 197, 94)),
            ("AVG LANE SHIFTS", f"{metrics.average_lane_changes:.2f}", (249, 166, 35)),
            ("AVG DECISIONS", f"{metrics.average_decisions:.2f}", (14, 165, 233)),
            (
                "STAY ACTIONS",
                f"{stay_count} · {metrics.action_percentage(STAY):.0f}%",
                (168, 85, 247),
            ),
            (
                "CHANGE ACTIONS",
                f"{change_count} · {metrics.action_percentage(CHANGE_LANE):.0f}%",
                (217, 70, 239),
            ),
        ]
        card_bottom = height - 146
        self._draw_cards(margin, card_bottom, content_width, cards)
        compact = height < 650
        run_bottom = 70.0
        run_height = 135.0 if compact else 172.0
        chart_bottom = run_bottom + run_height + 16.0
        chart_height = max(90.0, card_bottom - chart_bottom - 16.0)
        charts_width = content_width * 0.68
        category_width = charts_width * 0.38
        entity_width = charts_width - category_width - gap
        self._draw_distribution_chart(
            margin,
            chart_bottom,
            category_width,
            chart_height,
            key_prefix="batch_category",
            title="AVERAGE DEATHS BY CATEGORY",
            values=metrics.average_casualties_by_category,
            colors=CATEGORY_COLORS,
        )
        self._draw_distribution_chart(
            margin + category_width + gap,
            chart_bottom,
            entity_width,
            chart_height,
            key_prefix="batch_entity",
            title="AVERAGE DEATHS BY ENTITY",
            values=metrics.average_casualties_by_entity,
            labels=PEDESTRIAN_MODEL_LABELS,
            colors=PEDESTRIAN_MODEL_COLORS,
        )
        side_left = margin + charts_width + gap
        side_width = content_width - charts_width - gap
        side_gap = 10.0
        framework_ratio = 0.42 if metrics.implementation == LLM_MODE else 0.36
        framework_height = chart_height * framework_ratio
        lane_height = chart_height - framework_height - side_gap
        self._draw_lane_change_distribution(
            side_left,
            chart_bottom + framework_height + side_gap,
            side_width,
            lane_height,
            metrics,
        )
        self._draw_framework_metrics(
            side_left,
            chart_bottom,
            side_width,
            framework_height,
            metrics,
            report.error,
        )
        self._draw_run_table(
            margin,
            run_bottom,
            content_width,
            run_height,
            report,
            compact=compact,
        )

    @staticmethod
    def _signed(value: float, *, decimals: int = 2, suffix: str = "") -> str:
        if value == 0:
            return f"0{suffix}"
        return f"{value:+.{decimals}f}{suffix}"

    @staticmethod
    def _action_mix(metrics: ImplementationMetrics) -> str:
        return (
            f"{metrics.action_percentage(STAY):.0f}% / "
            f"{metrics.action_percentage(CHANGE_LANE):.0f}%"
        )

    def _comparison_rows(
        self,
        code: ImplementationMetrics,
        llm: ImplementationMetrics,
    ) -> list[tuple[str, str, str, str]]:
        rows = [
            (
                "Simulations",
                str(code.simulation_count),
                str(llm.simulation_count),
                "—",
            ),
            (
                "Total casualties",
                str(code.total_casualties),
                str(llm.total_casualties),
                self._signed(
                    llm.total_casualties - code.total_casualties,
                    decimals=0,
                ),
            ),
            (
                "Average casualties",
                f"{code.average_casualties:.2f}",
                f"{llm.average_casualties:.2f}",
                self._signed(llm.average_casualties - code.average_casualties),
            ),
            (
                "Zero-casualty rate",
                f"{code.zero_casualty_rate:.1f}%",
                f"{llm.zero_casualty_rate:.1f}%",
                self._signed(
                    llm.zero_casualty_rate - code.zero_casualty_rate,
                    decimals=1,
                    suffix=" pp",
                ),
            ),
            (
                "Average lane changes",
                f"{code.average_lane_changes:.2f}",
                f"{llm.average_lane_changes:.2f}",
                self._signed(
                    llm.average_lane_changes - code.average_lane_changes
                ),
            ),
            (
                "Average decisions",
                f"{code.average_decisions:.2f}",
                f"{llm.average_decisions:.2f}",
                self._signed(llm.average_decisions - code.average_decisions),
            ),
            (
                "STAY / CHANGE_LANE",
                self._action_mix(code),
                self._action_mix(llm),
                "—",
            ),
            (
                "LLM response latency",
                "N/A",
                (
                    f"{llm.average_llm_latency_ms:.0f} ms"
                    if llm.average_llm_latency_ms is not None
                    else "N/A"
                ),
                "—",
            ),
        ]
        framework_labels = dict.fromkeys(
            (
                *code.average_framework_metrics,
                *llm.average_framework_metrics,
            )
        )
        for label in framework_labels:
            code_value = code.average_framework_metrics.get(label, "N/A")
            llm_value = llm.average_framework_metrics.get(label, "N/A")
            delta = "—"
            try:
                delta = self._signed(float(llm_value) - float(code_value))
            except ValueError:
                pass
            rows.append((label, code_value, llm_value, delta))
        return rows

    def _draw_comparison_report(
        self,
        width: int,
        height: int,
        report: BatchReport,
        margin: float,
        content_width: float,
    ) -> None:
        code = report.metrics_for(CODE_MODE)
        llm = report.metrics_for(LLM_MODE)
        comparison = report.comparison_metrics
        cards = [
            (
                "PAIRED RUNS",
                str(comparison.paired_runs if comparison else 0),
                CODE_COLOR,
            ),
            (
                "CASUALTY Δ LLM-CODE",
                (
                    self._signed(comparison.casualty_difference, decimals=0)
                    if comparison
                    else "N/A"
                ),
                (239, 68, 68),
            ),
            (
                "DECISION AGREEMENT",
                (
                    f"{comparison.decision_agreement_rate:.1f}%"
                    if comparison
                    else "N/A"
                ),
                (168, 85, 247),
            ),
            (
                "CATEGORY AGREEMENT",
                (
                    f"{comparison.category_specific_agreement:.1f}%"
                    if comparison
                    else "N/A"
                ),
                (34, 197, 94),
            ),
            (
                "DIFFERENT OUTCOMES",
                str(comparison.different_final_results if comparison else 0),
                (249, 166, 35),
            ),
            (
                "LLM RESPONSE TIME",
                (
                    f"{llm.average_llm_latency_ms:.0f} ms"
                    if llm.average_llm_latency_ms is not None
                    else "N/A"
                ),
                LLM_COLOR,
            ),
        ]
        card_bottom = height - 146
        self._draw_cards(margin, card_bottom, content_width, cards)

        compact = height < 700
        table_top = card_bottom - 14.0
        table_height = 160.0 if compact else 190.0
        table_bottom = table_top - table_height
        self._draw_comparison_table(
            margin,
            table_bottom,
            content_width,
            table_height,
            self._comparison_rows(code, llm),
        )

        run_bottom = 70.0
        run_height = 112.0 if compact else 135.0
        charts_bottom = run_bottom + run_height + 14.0
        charts_top = table_bottom - 14.0
        charts_height = max(65.0, charts_top - charts_bottom)
        category_width = content_width * 0.40
        gap = 12.0
        self._draw_comparison_distribution_chart(
            margin,
            charts_bottom,
            category_width,
            charts_height,
            title="AVERAGE CASUALTIES BY CATEGORY",
            key_prefix="comparison_category",
            code_values=code.average_casualties_by_category,
            llm_values=llm.average_casualties_by_category,
        )
        self._draw_comparison_distribution_chart(
            margin + category_width + gap,
            charts_bottom,
            content_width - category_width - gap,
            charts_height,
            title="AVERAGE CASUALTIES BY ENTITY",
            key_prefix="comparison_entity",
            code_values=code.average_casualties_by_entity,
            llm_values=llm.average_casualties_by_entity,
            labels=PEDESTRIAN_MODEL_LABELS,
        )
        self._draw_pair_table(
            margin,
            run_bottom,
            content_width,
            run_height,
            report,
            compact=compact,
        )

    def _draw_comparison_table(
        self,
        left: float,
        bottom: float,
        width: float,
        height: float,
        rows: list[tuple[str, str, str, str]],
    ) -> None:
        self._panel(left, bottom, width, height, (168, 85, 247))
        self._text(
            "comparison_table_title",
            "IMPLEMENTATION COMPARISON",
            left + 15,
            bottom + height - 22,
            size=10,
            bold=True,
        )
        columns = (0.44, 0.65, 0.82, 0.97)
        for index, (header, ratio) in enumerate(
            zip(("METRIC", "CODE", "LLM", "Δ LLM − CODE"), columns)
        ):
            self._text(
                f"comparison_header_{index}",
                header,
                left + width * ratio,
                bottom + height - 43,
                color=(148, 163, 184),
                size=7,
                bold=True,
                anchor_x="right",
            )

        available_height = max(1.0, height - 58.0)
        spacing = min(19.0, available_height / max(1, len(rows)))
        font_size = 7 if len(rows) > 9 else 8
        y = bottom + height - 57
        for index, (label, code_value, llm_value, delta) in enumerate(rows):
            if index % 2 == 0:
                arcade.draw_lbwh_rectangle_filled(
                    left + 10,
                    y - spacing / 2,
                    width - 20,
                    spacing,
                    (31, 42, 55, 170),
                )
            values = (label, code_value, llm_value, delta)
            colors = (MUTED, CODE_COLOR, LLM_COLOR, TEXT)
            for column, (value, ratio, color) in enumerate(
                zip(values, columns, colors)
            ):
                self._text(
                    f"comparison_cell_{index}_{column}",
                    value,
                    left + width * ratio,
                    y,
                    color=color,
                    size=font_size,
                    bold=column > 0,
                    anchor_x="right",
                )
            y -= spacing

    def _draw_comparison_distribution_chart(
        self,
        left: float,
        bottom: float,
        width: float,
        height: float,
        *,
        title: str,
        key_prefix: str,
        code_values: dict[str, float],
        llm_values: dict[str, float],
        labels: dict[str, str] | None = None,
    ) -> None:
        self._panel(left, bottom, width, height)
        self._text(
            f"{key_prefix}_title",
            title,
            left + 12,
            bottom + height - 19,
            size=8,
            bold=True,
        )
        self._text(
            f"{key_prefix}_legend_code",
            "CODE",
            left + width - 76,
            bottom + height - 19,
            color=CODE_COLOR,
            size=7,
            bold=True,
            anchor_x="right",
        )
        self._text(
            f"{key_prefix}_legend_llm",
            "LLM",
            left + width - 12,
            bottom + height - 19,
            color=LLM_COLOR,
            size=7,
            bold=True,
            anchor_x="right",
        )

        keys = list(dict.fromkeys((*code_values, *llm_values))) or ["No data"]
        maximum = max(
            1.0,
            *(code_values.values() or [0.0]),
            *(llm_values.values() or [0.0]),
        )
        chart_left = left + 15
        chart_bottom = bottom + 25
        chart_top = bottom + height - 37
        slot = (width - 30) / len(keys)
        bar_width = min(18.0, slot * 0.24)
        label_size = 5 if len(keys) > 5 else 6
        show_values = height >= 120
        for index, key in enumerate(keys):
            center_x = chart_left + slot * (index + 0.5)
            for implementation_index, (value, color) in enumerate(
                (
                    (code_values.get(key, 0.0), CODE_COLOR),
                    (llm_values.get(key, 0.0), LLM_COLOR),
                )
            ):
                bar_height = max(
                    2.0,
                    (chart_top - chart_bottom) * value / maximum,
                )
                bar_center = center_x + (
                    -bar_width * 0.65
                    if implementation_index == 0
                    else bar_width * 0.65
                )
                arcade.draw_lbwh_rectangle_filled(
                    bar_center - bar_width / 2,
                    chart_bottom,
                    bar_width,
                    bar_height,
                    color,
                )
                if show_values:
                    self._text(
                        f"{key_prefix}_value_{index}_{implementation_index}",
                        f"{value:.2f}",
                        bar_center,
                        chart_bottom + bar_height + 7,
                        color=color,
                        size=6,
                        bold=True,
                        anchor_x="center",
                    )
            self._text(
                f"{key_prefix}_label_{index}",
                (labels or {}).get(key, key).upper(),
                center_x,
                bottom + 10,
                color=MUTED,
                size=label_size,
                anchor_x="center",
            )

    def _draw_pair_table(
        self,
        left: float,
        bottom: float,
        width: float,
        height: float,
        report: BatchReport,
        *,
        compact: bool,
    ) -> None:
        self._panel(left, bottom, width, height, (34, 197, 94))
        self._text(
            "pair_runs_title",
            "RECENT PAIRED RUNS  ·  SAME SCENARIO AND SEED",
            left + 15,
            bottom + height - 20,
            size=8,
            bold=True,
        )
        headers = (
            "PAIR",
            "SEED",
            "CODE DEATHS",
            "LLM DEATHS",
            "Δ",
            "SHIFTS C/L",
            "DECISIONS C/L",
        )
        columns = (0.03, 0.14, 0.31, 0.48, 0.61, 0.70, 0.85)
        for index, (header, ratio) in enumerate(zip(headers, columns)):
            self._text(
                f"pair_header_{index}",
                header,
                left + width * ratio,
                bottom + height - 42,
                color=MUTED,
                size=7,
                bold=True,
            )
        outcomes = (
            report.comparison_metrics.pair_outcomes
            if report.comparison_metrics is not None
            else ()
        )
        visible = outcomes[-(2 if compact else 3):]
        for row_index, outcome in enumerate(visible):
            y = bottom + height - 65 - row_index * 22
            values: tuple[Any, ...] = (
                outcome.pair_id,
                outcome.seed,
                outcome.code_casualties,
                outcome.llm_casualties,
                self._signed(outcome.casualty_difference, decimals=0),
                f"{outcome.code_lane_changes}/{outcome.llm_lane_changes}",
                f"{outcome.code_decisions}/{outcome.llm_decisions}",
            )
            for column_index, (value, ratio) in enumerate(zip(values, columns)):
                self._text(
                    f"pair_row_{row_index}_{column_index}",
                    str(value),
                    left + width * ratio,
                    y,
                    size=8,
                )

    def _draw_lane_change_distribution(
        self,
        left: float,
        bottom: float,
        width: float,
        height: float,
        metrics: ImplementationMetrics,
    ) -> None:
        shifts = range(metrics.maximum_lane_changes + 1)
        values = {
            str(shift): float(metrics.lane_change_distribution.get(shift, 0))
            for shift in shifts
        }
        labels = {
            str(shift): f"{shift} SHIFT" if shift == 1 else f"{shift} SHIFTS"
            for shift in shifts
        }
        palette = (
            (100, 116, 139),
            (249, 166, 35),
            (249, 115, 22),
            (239, 68, 68),
            (168, 85, 247),
        )
        colors = {
            str(shift): palette[shift % len(palette)]
            for shift in shifts
        }
        self._draw_distribution_chart(
            left,
            bottom,
            width,
            height,
            values,
            key_prefix="lane_change_distribution",
            title="LANE-CHANGE DISTRIBUTION",
            labels=labels,
            colors=colors,
            value_decimals=0,
        )

    def _draw_framework_metrics(
        self,
        left: float,
        bottom: float,
        width: float,
        height: float,
        metrics: ImplementationMetrics,
        error: str | None,
    ) -> None:
        self._panel(left, bottom, width, height, (34, 197, 94))
        self._text(
            "framework_metrics_title",
            "FRAMEWORK METRICS",
            left + 12,
            bottom + height - 19,
            size=9,
            bold=True,
        )

        llm_footer_height = 30.0 if metrics.implementation == LLM_MODE else 0.0
        error_height = 14.0 if error else 0.0
        footer_height = llm_footer_height + error_height
        card_bottom = bottom + 9 + footer_height
        card_top = bottom + height - 34
        card_height = max(18.0, card_top - card_bottom)
        items = list(metrics.average_framework_metrics.items())
        if not items:
            self._text(
                "framework_metrics_empty",
                "No framework-specific metrics",
                left + width / 2,
                card_bottom + card_height / 2,
                color=MUTED,
                size=8,
                anchor_x="center",
            )
        else:
            gap = 7.0
            card_width = (width - 20 - gap * (len(items) - 1)) / len(items)
            for index, (label, value) in enumerate(items):
                card_left = left + 10 + index * (card_width + gap)
                arcade.draw_lbwh_rectangle_filled(
                    card_left,
                    card_bottom,
                    card_width,
                    card_height,
                    (25, 34, 45, 245),
                )
                arcade.draw_lbwh_rectangle_outline(
                    card_left,
                    card_bottom,
                    card_width,
                    card_height,
                    BORDER,
                    1,
                )
                arcade.draw_lbwh_rectangle_filled(
                    card_left,
                    card_bottom + card_height - 2,
                    card_width,
                    2,
                    (34, 197, 94),
                )
                self._text(
                    f"framework_metric_label_{index}",
                    label.upper(),
                    card_left + 8,
                    card_bottom + card_height - 15,
                    color=MUTED,
                    size=6,
                    bold=True,
                )
                self._text(
                    f"framework_metric_value_{index}",
                    value,
                    card_left + 8,
                    card_bottom + max(10, card_height * 0.35),
                    size=11 if len(value) < 15 else 8,
                    bold=True,
                )

        if metrics.implementation == LLM_MODE:
            latency = (
                f"{metrics.average_llm_latency_ms:.0f} ms"
                if metrics.average_llm_latency_ms is not None
                else "N/A"
            )
            self._text(
                "framework_llm_metrics_primary",
                f"LLM: {latency} · Calls: {metrics.total_llm_calls}",
                left + 10,
                bottom + 24 + error_height,
                color=(251, 146, 60),
                size=7,
                bold=True,
            )
            self._text(
                "framework_llm_metrics_secondary",
                (
                    f"Failed: {metrics.failed_llm_calls} · "
                    f"Retries: {metrics.retries} · Fallbacks: {metrics.fallbacks}"
                ),
                left + 10,
                bottom + 10 + error_height,
                color=MUTED,
                size=6,
            )
        if error:
            self._text(
                "framework_metrics_error",
                error[:54],
                left + 10,
                bottom + 8,
                color=(248, 113, 113),
                size=6,
            )

    def _draw_distribution_chart(
        self,
        left: float,
        bottom: float,
        width: float,
        height: float,
        values: dict[str, float],
        *,
        key_prefix: str,
        title: str,
        labels: dict[str, str] | None = None,
        colors: dict[str, tuple[int, int, int]] | None = None,
        value_decimals: int = 2,
    ) -> None:
        self._panel(left, bottom, width, height)
        self._text(
            f"{key_prefix}_title",
            title,
            left + 15,
            bottom + height - 23,
            size=9,
            bold=True,
        )
        keys = list(values) or ["No data"]
        maximum = max(1.0, *(values.values() or [0.0]))
        chart_left = left + 18
        chart_bottom = bottom + 34
        chart_top = bottom + height - 48
        slot = (width - 36) / len(keys)
        label_size = 6 if len(keys) > 5 else 7
        value_size = 7 if len(keys) > 5 else 8
        for index, key in enumerate(keys):
            value = values.get(key, 0.0)
            bar_height = max(2.0, (chart_top - chart_bottom) * value / maximum)
            center_x = chart_left + slot * (index + 0.5)
            color = (colors or {}).get(key, (100, 116, 139))
            arcade.draw_lbwh_rectangle_filled(
                center_x - min(24, slot * 0.3),
                chart_bottom,
                min(48, slot * 0.6),
                bar_height,
                color,
            )
            self._text(
                f"{key_prefix}_value_{index}",
                f"{value:.{value_decimals}f}",
                center_x,
                chart_bottom + bar_height + 10,
                size=value_size,
                bold=True,
                anchor_x="center",
            )
            self._text(
                f"{key_prefix}_label_{index}",
                (labels or {}).get(key, key).upper(),
                center_x,
                bottom + 15,
                color=MUTED,
                size=label_size,
                anchor_x="center",
            )

    def _draw_run_table(
        self,
        left: float,
        bottom: float,
        width: float,
        height: float,
        report: BatchReport,
        *,
        compact: bool,
    ) -> None:
        self._panel(left, bottom, width, height, (34, 197, 94))
        self._text(
            "batch_runs_title",
            "RECENT RUNS  ·  DECISION HISTORIES RETAINED IN MEMORY",
            left + 15,
            bottom + height - 22,
            size=9,
            bold=True,
        )
        headers = ("RUN", "IMPLEMENTATION", "SEED", "DEATHS", "SHIFTS", "DECISIONS")
        columns = (0.03, 0.15, 0.43, 0.62, 0.76, 0.88)
        for index, (header, ratio) in enumerate(zip(headers, columns)):
            self._text(
                f"batch_header_{index}",
                header,
                left + width * ratio,
                bottom + height - 48,
                color=MUTED,
                size=7,
                bold=True,
            )
        visible = report.results[-(3 if compact else 4):]
        for row_index, result in enumerate(visible):
            y = bottom + height - 75 - row_index * 24
            values: tuple[Any, ...] = (
                result.pair_id or len(report.results) - len(visible) + row_index + 1,
                result.implementation,
                result.seed,
                result.total_deaths,
                f"{result.lane_changes_used}/{result.max_lane_changes}",
                result.number_of_decisions,
            )
            for column_index, (value, ratio) in enumerate(zip(values, columns)):
                self._text(
                    f"batch_row_{row_index}_{column_index}",
                    str(value),
                    left + width * ratio,
                    y,
                    size=8,
                )
