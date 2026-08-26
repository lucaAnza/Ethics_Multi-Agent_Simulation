"""Immutable configuration, progress and aggregate batch result models."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from itertools import zip_longest
from typing import Any

from decision_engine.modes import CODE_MODE, LLM_MODE
from ethics.base import DecisionRecord
from scenarios import (
    DEFAULT_RANDOM_SCENARIO_SETTINGS,
    validate_random_scenario_settings,
)

from .config import (
    BATCH_MODES,
    COMPARISON,
    MAX_LLM_BATCH_RUNS,
    ONLY_DETERMINISTIC,
)


def _average_counts(
    distributions: Iterable[Mapping[str, int]],
    denominator: int,
) -> dict[str, float]:
    totals: defaultdict[str, int] = defaultdict(int)
    for distribution in distributions:
        for key, count in distribution.items():
            totals[key] += count
    return {
        key: total / denominator
        for key, total in totals.items()
    }


@dataclass(frozen=True)
class BatchConfig:
    mode: str
    number_of_runs: int
    framework_name: str
    scenario_name: str
    random_seed: int | None
    scenario_definitions: dict[str, dict[str, list[dict[str, Any]]]]
    framework_settings: dict[str, Any]
    utilitarian_values: dict[str, float]
    additional_instructions: str
    world_width: int
    world_height: int
    vision_distance: float
    decision_distance: float
    max_lane_changes: int
    random_scenario_settings: dict[str, Any] = field(
        default_factory=DEFAULT_RANDOM_SCENARIO_SETTINGS.to_dict
    )

    def __post_init__(self) -> None:
        if self.mode not in BATCH_MODES:
            raise ValueError(f"Unsupported automated mode: {self.mode}")
        if self.number_of_runs < 1:
            raise ValueError("Number of simulations must be at least 1")
        if (
            self.mode != ONLY_DETERMINISTIC
            and self.number_of_runs > MAX_LLM_BATCH_RUNS
        ):
            raise ValueError(
                f"LLM batches are limited to {MAX_LLM_BATCH_RUNS} runs"
            )
        validate_random_scenario_settings(self.random_scenario_settings)


@dataclass(frozen=True)
class BatchSimulationResult:
    framework: str
    implementation: str
    scenario: str
    seed: int
    total_deaths: int
    deaths_by_category: dict[str, int]
    lane_changes_used: int
    max_lane_changes: int
    number_of_decisions: int
    decision_history: list[DecisionRecord]
    framework_specific_metrics: dict[str, str]
    deaths_by_entity: dict[str, int] = field(default_factory=dict)
    model: str | None = None
    average_latency_ms: float | None = None
    total_llm_calls: int = 0
    failed_calls: int = 0
    retries: int = 0
    fallbacks: int = 0
    pair_id: int | None = None


@dataclass(frozen=True)
class BatchProgress:
    mode: str
    completed_units: int
    total_units: int
    completed_simulations: int
    decisions_completed: int
    waiting_for_llm: bool
    current_run: str
    elapsed_seconds: float
    estimated_remaining_seconds: float | None
    finished: bool = False
    cancelled: bool = False
    error: str | None = None

    @property
    def fraction(self) -> float:
        if self.total_units <= 0:
            return 0.0
        return min(1.0, self.completed_units / self.total_units)


@dataclass(frozen=True)
class BatchReport:
    mode: str
    requested_units: int
    results: tuple[BatchSimulationResult, ...]
    cancelled: bool = False
    error: str | None = None
    average_deaths: float = field(init=False)
    average_deaths_by_category: dict[str, float] = field(init=False)
    average_deaths_by_entity: dict[str, float] = field(init=False)
    lane_change_distribution: dict[int, int] = field(init=False)
    average_decisions: float = field(init=False)
    average_llm_latency_ms: float | None = field(init=False)
    total_llm_calls: int = field(init=False)
    failed_llm_calls: int = field(init=False)
    retries: int = field(init=False)
    fallbacks: int = field(init=False)
    decision_agreement_rate: float | None = field(init=False)
    different_final_results: int | None = field(init=False)
    average_framework_metrics: dict[str, str] = field(init=False)

    def __post_init__(self) -> None:
        result_count = len(self.results)
        denominator = max(1, result_count)
        object.__setattr__(
            self,
            "average_deaths",
            sum(result.total_deaths for result in self.results) / denominator,
        )

        object.__setattr__(
            self,
            "average_deaths_by_category",
            _average_counts(
                (result.deaths_by_category for result in self.results),
                denominator,
            ),
        )
        object.__setattr__(
            self,
            "average_deaths_by_entity",
            _average_counts(
                (result.deaths_by_entity for result in self.results),
                denominator,
            ),
        )
        object.__setattr__(
            self,
            "lane_change_distribution",
            dict(sorted(Counter(r.lane_changes_used for r in self.results).items())),
        )
        object.__setattr__(
            self,
            "average_decisions",
            sum(result.number_of_decisions for result in self.results) / denominator,
        )

        llm_results = [r for r in self.results if r.implementation == LLM_MODE]
        weighted_latencies = [
            (r.average_latency_ms, r.number_of_decisions)
            for r in llm_results
            if r.average_latency_ms is not None and r.number_of_decisions > 0
        ]
        object.__setattr__(
            self,
            "average_llm_latency_ms",
            (
                sum(latency * count for latency, count in weighted_latencies)
                / sum(count for _latency, count in weighted_latencies)
                if weighted_latencies
                else None
            ),
        )
        object.__setattr__(
            self,
            "total_llm_calls",
            sum(r.total_llm_calls for r in llm_results),
        )
        object.__setattr__(
            self,
            "failed_llm_calls",
            sum(r.failed_calls for r in llm_results),
        )
        object.__setattr__(self, "retries", sum(r.retries for r in llm_results))
        object.__setattr__(self, "fallbacks", sum(r.fallbacks for r in llm_results))

        agreement, different = self._comparison_statistics()
        object.__setattr__(self, "decision_agreement_rate", agreement)
        object.__setattr__(self, "different_final_results", different)
        object.__setattr__(
            self,
            "average_framework_metrics",
            self._aggregate_framework_metrics(),
        )

    @property
    def total_simulations(self) -> int:
        return len(self.results)

    def _comparison_statistics(self) -> tuple[float | None, int | None]:
        if self.mode != COMPARISON:
            return None, None
        pairs: defaultdict[int, dict[str, BatchSimulationResult]] = defaultdict(dict)
        for result in self.results:
            if result.pair_id is not None:
                pairs[result.pair_id][result.implementation] = result

        agreements = 0
        compared = 0
        different_results = 0
        complete_pairs = 0
        for pair in pairs.values():
            code = pair.get(CODE_MODE)
            llm = pair.get(LLM_MODE)
            if code is None or llm is None:
                continue
            complete_pairs += 1
            code_actions = [record.get("action") for record in code.decision_history]
            llm_actions = [record.get("action") for record in llm.decision_history]
            for code_action, llm_action in zip_longest(code_actions, llm_actions):
                compared += 1
                agreements += int(code_action == llm_action)
            if (
                code.total_deaths != llm.total_deaths
                or code.deaths_by_category != llm.deaths_by_category
                or code.deaths_by_entity != llm.deaths_by_entity
            ):
                different_results += 1
        if complete_pairs == 0:
            return None, None
        rate = 100.0 if compared == 0 else agreements * 100.0 / compared
        return rate, different_results

    def _aggregate_framework_metrics(self) -> dict[str, str]:
        numeric: defaultdict[str, list[float]] = defaultdict(list)
        categorical: defaultdict[str, set[str]] = defaultdict(set)
        for result in self.results:
            for label, raw_value in result.framework_specific_metrics.items():
                if label.lower() == "decisions":
                    continue
                try:
                    numeric[label].append(float(raw_value))
                except (TypeError, ValueError):
                    categorical[label].add(str(raw_value))
        metrics = {
            f"Average {label}": f"{sum(values) / len(values):.2f}"
            for label, values in numeric.items()
        }
        metrics.update(
            {
                label: next(iter(values)) if len(values) == 1 else "Mixed"
                for label, values in categorical.items()
            }
        )
        return metrics
