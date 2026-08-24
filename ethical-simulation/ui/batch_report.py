"""Arcade rendering for automated-simulation progress and aggregate reports."""

from __future__ import annotations

from typing import Any

import arcade

from automated import BatchProgress, BatchReport


TEXT = (238, 243, 248)
MUTED = (155, 170, 185)
PANEL = (25, 34, 45, 245)
BORDER = (61, 76, 94)
ACCENT = (14, 165, 233)


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
        state = "CANCELLED · PARTIAL RESULTS" if report.cancelled else report.mode.upper()
        self._text(
            "batch_subtitle",
            state,
            width / 2,
            height - 59,
            color=(251, 146, 60) if report.cancelled else MUTED,
            size=9,
            anchor_x="center",
        )

        cards = [
            ("SIMULATIONS", str(report.total_simulations), (59, 130, 246)),
            ("AVG DEATHS", f"{report.average_deaths:.2f}", (239, 68, 68)),
            ("AVG DECISIONS", f"{report.average_decisions:.2f}", (34, 197, 94)),
        ]
        has_llm_results = any(
            result.implementation == "llm-agent" for result in report.results
        )
        if report.decision_agreement_rate is not None:
            cards.append(
                (
                    "DECISION AGREEMENT",
                    f"{report.decision_agreement_rate:.1f}%",
                    (168, 85, 247),
                )
            )
        elif has_llm_results:
            cards.append(
                (
                    "AVG LLM LATENCY",
                    (
                        f"{report.average_llm_latency_ms:.0f} ms"
                        if report.average_llm_latency_ms is not None
                        else "N/A"
                    ),
                    (168, 85, 247),
                )
            )
        else:
            cards.append(("MODE", "CODE", (249, 166, 35)))
        gap = 12.0
        card_width = (content_width - gap * 3) / 4
        card_bottom = height - 146
        for index, (label, value, color) in enumerate(cards):
            left = margin + index * (card_width + gap)
            self._panel(left, card_bottom, card_width, 68, color)
            self._text(
                f"batch_card_label_{index}",
                label,
                left + 12,
                card_bottom + 45,
                color=MUTED,
                size=8,
                bold=True,
            )
            self._text(
                f"batch_card_value_{index}",
                value,
                left + 12,
                card_bottom + 21,
                size=17,
                bold=True,
            )

        compact = height < 650
        run_bottom = 70.0
        run_height = 135.0 if compact else 172.0
        chart_bottom = run_bottom + run_height + 16.0
        chart_height = max(90.0, card_bottom - chart_bottom - 16.0)
        chart_width = content_width * 0.56
        self._draw_category_chart(
            margin,
            chart_bottom,
            chart_width,
            chart_height,
            report.average_deaths_by_category,
        )
        self._draw_details(
            margin + chart_width + gap,
            chart_bottom,
            content_width - chart_width - gap,
            chart_height,
            report,
        )
        self._draw_run_table(
            margin,
            run_bottom,
            content_width,
            run_height,
            report,
            compact=compact,
        )

    def _draw_category_chart(
        self,
        left: float,
        bottom: float,
        width: float,
        height: float,
        values: dict[str, float],
    ) -> None:
        self._panel(left, bottom, width, height)
        self._text(
            "batch_categories_title",
            "AVERAGE DEATHS BY CATEGORY",
            left + 15,
            bottom + height - 23,
            size=10,
            bold=True,
        )
        categories = list(values) or ["No deaths"]
        maximum = max(1.0, *(values.values() or [0.0]))
        chart_left = left + 42
        chart_bottom = bottom + 34
        chart_top = bottom + height - 48
        slot = (width - 68) / len(categories)
        for index, category in enumerate(categories):
            value = values.get(category, 0.0)
            bar_height = max(2.0, (chart_top - chart_bottom) * value / maximum)
            center_x = chart_left + slot * (index + 0.5)
            color = {
                "Child": (59, 130, 246),
                "Adult": (249, 115, 22),
                "Elderly": (168, 85, 247),
                "Custom": (34, 197, 94),
            }.get(category, (100, 116, 139))
            arcade.draw_lbwh_rectangle_filled(
                center_x - min(28, slot * 0.3),
                chart_bottom,
                min(56, slot * 0.6),
                bar_height,
                color,
            )
            self._text(
                f"batch_category_value_{index}",
                f"{value:.2f}",
                center_x,
                chart_bottom + bar_height + 10,
                size=8,
                bold=True,
                anchor_x="center",
            )
            self._text(
                f"batch_category_label_{index}",
                category.upper(),
                center_x,
                bottom + 15,
                color=MUTED,
                size=7,
                anchor_x="center",
            )

    def _draw_details(
        self,
        left: float,
        bottom: float,
        width: float,
        height: float,
        report: BatchReport,
    ) -> None:
        self._panel(left, bottom, width, height, (249, 146, 60))
        self._text(
            "batch_details_title",
            "BATCH METRICS",
            left + 15,
            bottom + height - 23,
            size=10,
            bold=True,
        )
        lane_distribution = ", ".join(
            f"{shifts} shifts: {count}"
            for shifts, count in report.lane_change_distribution.items()
        ) or "No completed runs"
        rows: list[tuple[str, str]] = [
            ("Lane-change distribution", lane_distribution),
        ]
        rows.extend(report.average_framework_metrics.items())
        if any(result.implementation == "llm-agent" for result in report.results):
            rows.extend(
                [
                    ("LLM calls", str(report.total_llm_calls)),
                    ("Failed calls / retries", f"{report.failed_llm_calls} / {report.retries}"),
                    ("Fallbacks", str(report.fallbacks)),
                ]
            )
        if report.different_final_results is not None:
            rows.append(
                ("Different final results", str(report.different_final_results))
            )
        if report.error:
            rows.append(("Batch error", report.error[:52]))
        y = bottom + height - 52
        for index, (label, value) in enumerate(rows[:7]):
            self._text(
                f"batch_detail_label_{index}",
                label,
                left + 15,
                y,
                color=MUTED,
                size=8,
            )
            self._text(
                f"batch_detail_value_{index}",
                value,
                left + width - 15,
                y,
                size=9,
                bold=True,
                anchor_x="right",
            )
            y -= 27

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
