"""Immutable configuration, progress and aggregate batch result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from decision_engine.modes import LLM_MODE
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
from .statistics import (
    ImplementationMetrics,
    PairedComparisonMetrics,
    aggregate_results,
    compare_paired_results,
)


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
    implementation_metrics: dict[str, ImplementationMetrics] = field(init=False)
    overall_metrics: ImplementationMetrics = field(init=False)
    comparison_metrics: PairedComparisonMetrics | None = field(init=False)
    total_casualties: int = field(init=False)
    average_deaths: float = field(init=False)
    average_deaths_by_category: dict[str, float] = field(init=False)
    average_deaths_by_entity: dict[str, float] = field(init=False)
    average_lane_changes: float = field(init=False)
    lane_change_distribution: dict[int, int] = field(init=False)
    average_decisions: float = field(init=False)
    action_counts: dict[str, int] = field(init=False)
    zero_casualty_rate: float = field(init=False)
    average_llm_latency_ms: float | None = field(init=False)
    total_llm_calls: int = field(init=False)
    failed_llm_calls: int = field(init=False)
    retries: int = field(init=False)
    fallbacks: int = field(init=False)
    decision_agreement_rate: float | None = field(init=False)
    casualty_difference: int | None = field(init=False)
    average_casualty_difference: float | None = field(init=False)
    category_specific_agreement: float | None = field(init=False)
    different_final_results: int | None = field(init=False)
    average_framework_metrics: dict[str, str] = field(init=False)

    def __post_init__(self) -> None:
        implementations = dict.fromkeys(
            result.implementation for result in self.results
        )
        implementation_metrics = {
            implementation: aggregate_results(
                (
                    result
                    for result in self.results
                    if result.implementation == implementation
                ),
                implementation=implementation,
            )
            for implementation in implementations
        }
        overall = aggregate_results(self.results, implementation="all")
        comparison = (
            compare_paired_results(self.results)
            if self.mode == COMPARISON
            else None
        )
        object.__setattr__(self, "implementation_metrics", implementation_metrics)
        object.__setattr__(self, "overall_metrics", overall)
        object.__setattr__(self, "comparison_metrics", comparison)
        object.__setattr__(self, "total_casualties", overall.total_casualties)
        object.__setattr__(
            self,
            "average_deaths",
            overall.average_casualties,
        )
        object.__setattr__(
            self,
            "average_deaths_by_category",
            overall.average_casualties_by_category,
        )
        object.__setattr__(
            self,
            "average_deaths_by_entity",
            overall.average_casualties_by_entity,
        )
        object.__setattr__(self, "average_lane_changes", overall.average_lane_changes)
        object.__setattr__(
            self,
            "lane_change_distribution",
            overall.lane_change_distribution,
        )
        object.__setattr__(self, "average_decisions", overall.average_decisions)
        object.__setattr__(self, "action_counts", overall.action_counts)
        object.__setattr__(self, "zero_casualty_rate", overall.zero_casualty_rate)

        llm_metrics = implementation_metrics.get(LLM_MODE)
        object.__setattr__(
            self,
            "average_llm_latency_ms",
            llm_metrics.average_llm_latency_ms if llm_metrics else None,
        )
        object.__setattr__(
            self,
            "total_llm_calls",
            llm_metrics.total_llm_calls if llm_metrics else 0,
        )
        object.__setattr__(
            self,
            "failed_llm_calls",
            llm_metrics.failed_llm_calls if llm_metrics else 0,
        )
        object.__setattr__(self, "retries", llm_metrics.retries if llm_metrics else 0)
        object.__setattr__(
            self,
            "fallbacks",
            llm_metrics.fallbacks if llm_metrics else 0,
        )
        object.__setattr__(
            self,
            "decision_agreement_rate",
            comparison.decision_agreement_rate if comparison else None,
        )
        object.__setattr__(
            self,
            "casualty_difference",
            comparison.casualty_difference if comparison else None,
        )
        object.__setattr__(
            self,
            "average_casualty_difference",
            comparison.average_casualty_difference if comparison else None,
        )
        object.__setattr__(
            self,
            "category_specific_agreement",
            comparison.category_specific_agreement if comparison else None,
        )
        object.__setattr__(
            self,
            "different_final_results",
            comparison.different_final_results if comparison else None,
        )
        object.__setattr__(
            self,
            "average_framework_metrics",
            overall.average_framework_metrics,
        )

    @property
    def total_simulations(self) -> int:
        return len(self.results)

    def metrics_for(self, implementation: str) -> ImplementationMetrics:
        """Return per-implementation values, including an empty safe result."""
        return self.implementation_metrics.get(implementation) or aggregate_results(
            (),
            implementation=implementation,
        )

    @property
    def primary_metrics(self) -> ImplementationMetrics:
        """Return the single implementation, or overall values as a fallback."""
        if len(self.implementation_metrics) == 1:
            return next(iter(self.implementation_metrics.values()))
        return self.overall_metrics
