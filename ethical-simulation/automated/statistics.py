"""Aggregation services for automated-simulation reports."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from itertools import zip_longest
from typing import Any, Protocol

from decision_engine.modes import CODE_MODE, LLM_MODE
from ethics.base import CHANGE_LANE, STAY


class SimulationResult(Protocol):
    """Minimal result contract consumed by the statistics layer."""

    implementation: str
    seed: int
    total_deaths: int
    deaths_by_category: Mapping[str, int]
    deaths_by_entity: Mapping[str, int]
    lane_changes_used: int
    max_lane_changes: int
    number_of_decisions: int
    decision_history: list[dict[str, Any]]
    framework_specific_metrics: Mapping[str, str]
    average_latency_ms: float | None
    total_llm_calls: int
    failed_calls: int
    retries: int
    fallbacks: int
    pair_id: int | None


@dataclass(frozen=True)
class ImplementationMetrics:
    """Aggregate values for one implementation or a complete batch."""

    implementation: str
    simulation_count: int
    total_casualties: int
    average_casualties: float
    average_casualties_by_category: dict[str, float]
    average_casualties_by_entity: dict[str, float]
    average_lane_changes: float
    maximum_lane_changes: int
    lane_change_distribution: dict[int, int]
    average_decisions: float
    action_counts: dict[str, int]
    zero_casualty_rate: float
    average_framework_metrics: dict[str, str]
    average_llm_latency_ms: float | None
    total_llm_calls: int
    failed_llm_calls: int
    retries: int
    fallbacks: int

    @property
    def total_actions(self) -> int:
        return sum(self.action_counts.values())

    def action_percentage(self, action: str) -> float:
        if self.total_actions == 0:
            return 0.0
        return self.action_counts.get(action, 0) * 100.0 / self.total_actions


@dataclass(frozen=True)
class PairedRunOutcome:
    """Compact outcome comparison for one shared scenario seed."""

    pair_id: int
    seed: int
    code_casualties: int
    llm_casualties: int
    code_lane_changes: int
    llm_lane_changes: int
    code_decisions: int
    llm_decisions: int

    @property
    def casualty_difference(self) -> int:
        return self.llm_casualties - self.code_casualties


@dataclass(frozen=True)
class PairedComparisonMetrics:
    """Statistics that are meaningful only for matched Code/LLM runs."""

    paired_runs: int
    casualty_difference: int
    average_casualty_difference: float
    decision_agreement_rate: float
    category_specific_agreement: float
    different_final_results: int
    pair_outcomes: tuple[PairedRunOutcome, ...]


def _average_counts(
    distributions: Iterable[Mapping[str, int]],
    denominator: int,
) -> dict[str, float]:
    totals: defaultdict[str, int] = defaultdict(int)
    for distribution in distributions:
        for key, count in distribution.items():
            totals[key] += count
    return {key: total / denominator for key, total in totals.items()}


def _average_framework_metrics(
    results: tuple[SimulationResult, ...],
) -> dict[str, str]:
    numeric: defaultdict[str, list[float]] = defaultdict(list)
    categorical: defaultdict[str, set[str]] = defaultdict(set)
    for result in results:
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


def aggregate_results(
    results: Iterable[SimulationResult],
    *,
    implementation: str,
) -> ImplementationMetrics:
    """Aggregate one homogeneous result set without UI-specific formatting."""
    items = tuple(results)
    count = len(items)
    denominator = max(1, count)
    total_casualties = sum(result.total_deaths for result in items)
    action_counts = {STAY: 0, CHANGE_LANE: 0}
    for result in items:
        for record in result.decision_history:
            action = record.get("action")
            if action in action_counts:
                action_counts[action] += 1

    weighted_latencies = [
        (result.average_latency_ms, result.number_of_decisions)
        for result in items
        if result.average_latency_ms is not None
        and result.number_of_decisions > 0
    ]
    latency_weight = sum(weight for _latency, weight in weighted_latencies)
    average_latency = (
        sum(latency * weight for latency, weight in weighted_latencies)
        / latency_weight
        if latency_weight
        else None
    )

    return ImplementationMetrics(
        implementation=implementation,
        simulation_count=count,
        total_casualties=total_casualties,
        average_casualties=total_casualties / denominator,
        average_casualties_by_category=_average_counts(
            (result.deaths_by_category for result in items),
            denominator,
        ),
        average_casualties_by_entity=_average_counts(
            (result.deaths_by_entity for result in items),
            denominator,
        ),
        average_lane_changes=(
            sum(result.lane_changes_used for result in items) / denominator
        ),
        maximum_lane_changes=max(
            (result.max_lane_changes for result in items),
            default=0,
        ),
        lane_change_distribution=dict(
            sorted(Counter(result.lane_changes_used for result in items).items())
        ),
        average_decisions=(
            sum(result.number_of_decisions for result in items) / denominator
        ),
        action_counts=action_counts,
        zero_casualty_rate=(
            sum(result.total_deaths == 0 for result in items)
            * 100.0
            / denominator
        ),
        average_framework_metrics=_average_framework_metrics(items),
        average_llm_latency_ms=average_latency,
        total_llm_calls=sum(result.total_llm_calls for result in items),
        failed_llm_calls=sum(result.failed_calls for result in items),
        retries=sum(result.retries for result in items),
        fallbacks=sum(result.fallbacks for result in items),
    )


def _distribution_similarity(
    first: Mapping[str, int],
    second: Mapping[str, int],
) -> float:
    """Return weighted-Jaccard similarity for two casualty distributions."""
    keys = first.keys() | second.keys()
    union = sum(max(first.get(key, 0), second.get(key, 0)) for key in keys)
    if union == 0:
        return 100.0
    overlap = sum(min(first.get(key, 0), second.get(key, 0)) for key in keys)
    return overlap * 100.0 / union


def compare_paired_results(
    results: Iterable[SimulationResult],
) -> PairedComparisonMetrics | None:
    """Compare only complete Code/LLM pairs sharing the same pair identifier."""
    pairs: defaultdict[int, dict[str, SimulationResult]] = defaultdict(dict)
    for result in results:
        if result.pair_id is not None:
            pairs[result.pair_id][result.implementation] = result

    agreements = 0
    compared_decisions = 0
    category_similarities: list[float] = []
    different_results = 0
    outcomes: list[PairedRunOutcome] = []
    for pair_id, pair in sorted(pairs.items()):
        code = pair.get(CODE_MODE)
        llm = pair.get(LLM_MODE)
        if code is None or llm is None:
            continue

        code_actions = [record.get("action") for record in code.decision_history]
        llm_actions = [record.get("action") for record in llm.decision_history]
        for code_action, llm_action in zip_longest(code_actions, llm_actions):
            compared_decisions += 1
            agreements += int(code_action == llm_action)

        category_similarities.append(
            _distribution_similarity(
                code.deaths_by_category,
                llm.deaths_by_category,
            )
        )
        if (
            code.total_deaths != llm.total_deaths
            or code.deaths_by_category != llm.deaths_by_category
            or code.deaths_by_entity != llm.deaths_by_entity
        ):
            different_results += 1
        outcomes.append(
            PairedRunOutcome(
                pair_id=pair_id,
                seed=code.seed,
                code_casualties=code.total_deaths,
                llm_casualties=llm.total_deaths,
                code_lane_changes=code.lane_changes_used,
                llm_lane_changes=llm.lane_changes_used,
                code_decisions=code.number_of_decisions,
                llm_decisions=llm.number_of_decisions,
            )
        )

    if not outcomes:
        return None
    casualty_difference = sum(outcome.casualty_difference for outcome in outcomes)
    decision_agreement = (
        100.0
        if compared_decisions == 0
        else agreements * 100.0 / compared_decisions
    )
    return PairedComparisonMetrics(
        paired_runs=len(outcomes),
        casualty_difference=casualty_difference,
        average_casualty_difference=casualty_difference / len(outcomes),
        decision_agreement_rate=decision_agreement,
        category_specific_agreement=(
            sum(category_similarities) / len(category_similarities)
        ),
        different_final_results=different_results,
        pair_outcomes=tuple(outcomes),
    )
