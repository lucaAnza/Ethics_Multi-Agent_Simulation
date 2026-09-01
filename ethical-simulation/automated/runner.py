"""Cancellable background runner for rendering-free simulation batches."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from copy import deepcopy
import random
import threading
from time import monotonic
from typing import Callable

from app_logging import application_logger
from decision_engine import (
    CODE_MODE,
    LLM_MODE,
    DecisionEngineFactory,
    LLMDecisionEngine,
)
from ethics.utils.factory import EthicalFrameworkFactory
from scenarios import RANDOM_SCENARIO_NAME
from simulation.engine import SimulationEngine
from simulation.statistics import (
    casualty_category_counts,
    casualty_entity_counts,
)
from simulation.world import World

from .config import (
    COMPARISON,
    FIXED_DELTA_TIME,
    MAX_SIMULATED_SECONDS,
    ONLY_DETERMINISTIC,
)
from .models import (
    BatchConfig,
    BatchProgress,
    BatchReport,
    BatchSimulationResult,
)


class AutomatedSimulationRunner:
    """Execute batches off the Arcade event loop and expose thread-safe progress."""

    def __init__(
        self,
        llm_engine_factory: Callable[[], LLMDecisionEngine] | None = None,
    ) -> None:
        self._llm_engine_factory = (
            llm_engine_factory or DecisionEngineFactory.create_llm
        )
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="automated-simulation",
        )
        self._future: Future[BatchReport] | None = None
        self._cancel_event = threading.Event()
        self._lock = threading.Lock()
        self._progress = BatchProgress(
            mode=ONLY_DETERMINISTIC,
            completed_units=0,
            total_units=0,
            completed_simulations=0,
            decisions_completed=0,
            waiting_for_llm=False,
            current_run="Not started",
            elapsed_seconds=0.0,
            estimated_remaining_seconds=None,
        )

    @property
    def is_running(self) -> bool:
        return self._future is not None and not self._future.done()

    def start(self, config: BatchConfig) -> None:
        if self.is_running:
            raise RuntimeError("An automated simulation is already running")
        self._cancel_event.clear()
        self._set_progress(
            mode=config.mode,
            completed_units=0,
            total_units=config.number_of_runs,
            completed_simulations=0,
            decisions_completed=0,
            waiting_for_llm=False,
            current_run="Preparing batch",
            elapsed_seconds=0.0,
            estimated_remaining_seconds=None,
        )
        self._future = self._executor.submit(self._run_batch, deepcopy(config))

    def cancel(self) -> None:
        self._cancel_event.set()

    def progress(self) -> BatchProgress:
        with self._lock:
            return self._progress

    def poll_report(self) -> BatchReport | None:
        future = self._future
        if future is None or not future.done():
            return None
        self._future = None
        return future.result()

    def _set_progress(self, **changes) -> None:
        with self._lock:
            current = self._progress.__dict__.copy()
            current.update(changes)
            self._progress = BatchProgress(**current)

    def _update_timing(self, started_at: float, completed_units: int) -> None:
        elapsed = monotonic() - started_at
        progress = self.progress()
        remaining = None
        if completed_units > 0:
            remaining = max(
                0.0,
                elapsed / completed_units * (progress.total_units - completed_units),
            )
        self._set_progress(
            elapsed_seconds=elapsed,
            estimated_remaining_seconds=remaining,
        )

    def _run_batch(self, config: BatchConfig) -> BatchReport:
        started_at = monotonic()
        results: list[BatchSimulationResult] = []
        base_seed = (
            config.random_seed
            if config.random_seed is not None
            else random.SystemRandom().randrange(0, 2**31)
        )
        try:
            for run_index in range(config.number_of_runs):
                if self._cancel_event.is_set():
                    break
                seed = base_seed + run_index
                pair_id = run_index + 1 if config.mode == COMPARISON else None
                results_before_unit = len(results)
                implementations = (
                    (CODE_MODE, LLM_MODE)
                    if config.mode == COMPARISON
                    else (
                        (CODE_MODE,)
                        if config.mode == ONLY_DETERMINISTIC
                        else (LLM_MODE,)
                    )
                )
                for implementation in implementations:
                    if self._cancel_event.is_set():
                        break
                    self._set_progress(
                        current_run=(
                            (
                                "Pair"
                                if config.mode == COMPARISON
                                else "Simulation"
                            )
                            + f" {run_index + 1} / {config.number_of_runs} · "
                            f"{implementation}"
                        ),
                        waiting_for_llm=False,
                    )
                    result = self._run_one(
                        config,
                        implementation=implementation,
                        seed=seed,
                        pair_id=pair_id,
                        started_at=started_at,
                    )
                    if result is not None:
                        results.append(result)
                        self._set_progress(completed_simulations=len(results))

                expected_results = 2 if config.mode == COMPARISON else 1
                unit_completed = len(results) - results_before_unit == expected_results
                completed_units = run_index + int(unit_completed)
                self._set_progress(completed_units=completed_units)
                self._update_timing(started_at, completed_units)

            cancelled = self._cancel_event.is_set()
            report = BatchReport(
                mode=config.mode,
                requested_units=config.number_of_runs,
                results=tuple(results),
                cancelled=cancelled,
            )
            self._set_progress(
                finished=True,
                cancelled=cancelled,
                waiting_for_llm=False,
                current_run="Cancelled" if cancelled else "Completed",
                elapsed_seconds=monotonic() - started_at,
                estimated_remaining_seconds=0.0,
            )
            return report
        except Exception as error:
            message = str(error) or type(error).__name__
            self._set_progress(
                finished=True,
                waiting_for_llm=False,
                current_run="Failed",
                elapsed_seconds=monotonic() - started_at,
                error=message,
            )
            return BatchReport(
                mode=config.mode,
                requested_units=config.number_of_runs,
                results=tuple(results),
                cancelled=self._cancel_event.is_set(),
                error=message,
            )

    def _run_one(
        self,
        config: BatchConfig,
        *,
        implementation: str,
        seed: int,
        pair_id: int | None,
        started_at: float,
    ) -> BatchSimulationResult | None:
        framework = EthicalFrameworkFactory.create(
            config.framework_name,
            config.framework_settings,
            utilitarian_values=config.utilitarian_values,
        )
        world = World(
            config.world_width,
            config.world_height,
            config.scenario_name,
            config.scenario_definitions,
            random_seed=seed,
            random_scenario_settings=config.random_scenario_settings,
            rendering_enabled=False,
        )
        if config.scenario_name != RANDOM_SCENARIO_NAME:
            world.configure_vehicle(
                vision_distance=config.vision_distance,
                decision_distance=config.decision_distance,
                max_spostamenti=config.max_lane_changes,
            )
        llm_engine = self._llm_engine_factory() if implementation == LLM_MODE else None
        engine = SimulationEngine(
            world=world,
            framework_name=config.framework_name,
            implementation=implementation,
            framework=framework,
            framework_settings_provider=lambda _name: config.framework_settings,
            additional_instructions_provider=(
                lambda _name: config.additional_instructions
            ),
            llm_decision_engine=llm_engine,
            owns_llm_engine=True,
        )
        simulated_seconds = 0.0
        progress_waiting = False
        last_timing_update = 0.0
        try:
            while not engine.finished and simulated_seconds < MAX_SIMULATED_SECONDS:
                if self._cancel_event.is_set():
                    engine.cancel_pending_decision()
                    return None
                step = engine.step(FIXED_DELTA_TIME)
                if step.decision_event is not None:
                    progress = self.progress()
                    self._set_progress(
                        decisions_completed=progress.decisions_completed + 1,
                    )
                    if implementation == LLM_MODE:
                        event = step.decision_event
                        application_logger.log_decision(
                            framework=event.framework_name,
                            implementation=event.implementation,
                            model=event.applied_decision.details.get("model"),
                            current_lane_count=len(
                                event.context.current_lane_entities
                            ),
                            other_lane_count=len(
                                event.context.other_lane_entities
                            ),
                            framework_action=event.recommended_decision.action,
                            applied_action=event.applied_decision.action,
                            reason=event.applied_decision.reason,
                            lane_change_blocked=(
                                event.recommended_decision.action == "CHANGE_LANE"
                                and not event.lane_change_started
                            ),
                            llm_request=event.llm_request,
                            llm_response=event.llm_response,
                            llm_raw_response=event.llm_raw_response,
                            latency_ms=event.applied_decision.details.get(
                                "latency_ms"
                            ),
                            attempts=event.applied_decision.details.get(
                                "attempts"
                            ),
                        )
                if engine.is_waiting_for_llm:
                    if not progress_waiting:
                        self._set_progress(waiting_for_llm=True)
                        progress_waiting = True
                    self._cancel_event.wait(0.01)
                    now = monotonic()
                    if now - last_timing_update >= 0.1:
                        self._update_timing(
                            started_at,
                            self.progress().completed_units,
                        )
                        last_timing_update = now
                else:
                    if progress_waiting:
                        self._set_progress(waiting_for_llm=False)
                        progress_waiting = False
                    simulated_seconds += FIXED_DELTA_TIME

            if not engine.finished:
                raise RuntimeError(
                    "A simulation exceeded 180 virtual seconds; check vehicle speed"
                )
            return self._collect_result(
                config,
                implementation,
                seed,
                pair_id,
                world,
                framework,
            )
        finally:
            engine.close()

    @staticmethod
    def _collect_result(
        config: BatchConfig,
        implementation: str,
        seed: int,
        pair_id: int | None,
        world: World,
        framework,
    ) -> BatchSimulationResult:
        dead = world.dead_pedestrians()
        casualties = [
            {"model": pedestrian.model, "label": pedestrian.label}
            for pedestrian in dead
        ]
        history = deepcopy(framework.decision_history)
        metrics = dict(framework.summary(casualties))
        llm_records = [record for record in history if record.get("mode") == LLM_MODE]
        latencies = [
            float(record["latency_ms"])
            for record in llm_records
            if isinstance(record.get("latency_ms"), (int, float))
        ]
        attempts = [max(0, int(record.get("attempts", 0))) for record in llm_records]
        fallbacks = sum(bool(record.get("fallback")) for record in llm_records)
        failed_calls = sum(
            attempt if record.get("fallback") else max(0, attempt - 1)
            for attempt, record in zip(attempts, llm_records)
        )
        models = [str(record["model"]) for record in llm_records if record.get("model")]
        return BatchSimulationResult(
            framework=config.framework_name,
            implementation=implementation,
            scenario=config.scenario_name,
            seed=seed,
            total_deaths=len(dead),
            deaths_by_category=casualty_category_counts(dead),
            deaths_by_entity=casualty_entity_counts(dead),
            lane_changes_used=world.lane_changes_used,
            max_lane_changes=world.max_spostamenti,
            number_of_decisions=len(history),
            decision_history=history,
            framework_specific_metrics=metrics,
            model=models[0] if models else None,
            average_latency_ms=(sum(latencies) / len(latencies) if latencies else None),
            total_llm_calls=sum(attempts),
            failed_calls=failed_calls,
            retries=sum(max(0, attempt - 1) for attempt in attempts),
            fallbacks=fallbacks,
            pair_id=pair_id,
        )

    def close(self) -> None:
        self.cancel()
        self._executor.shutdown(wait=False, cancel_futures=True)
