"""Shared rendering-independent execution engine for one simulation run."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from decision_engine import (
    DRIVING,
    EXECUTING_DECISION,
    WAITING_FOR_LLM,
    CodeDecisionEngine,
    LLMDecisionEngine,
)
from decision_engine.modes import CODE_MODE, LLM_MODE
from ethics.base import (
    CHANGE_LANE,
    STAY,
    DecisionContext,
    EthicalDecision,
    EthicalFramework,
)
from llm.errors import safe_error_message

from .world import DetectedIncident, World


@dataclass(frozen=True)
class SimulationDecisionEvent:
    """One completed and applied ethical decision."""

    framework_name: str
    implementation: str
    context: DecisionContext
    recommended_decision: EthicalDecision
    applied_decision: EthicalDecision
    lane_change_started: bool
    llm_request: str | None = None
    llm_response: str | None = None
    llm_raw_response: str | None = None


@dataclass(frozen=True)
class SimulationStepResult:
    reached_tunnel: bool
    decision_event: SimulationDecisionEvent | None = None


class SimulationEngine:
    """Advance movement, perception, decisions and collisions without drawing."""

    def __init__(
        self,
        *,
        world: World,
        framework_name: str,
        implementation: str,
        framework: EthicalFramework,
        framework_settings_provider: Callable[[str], Mapping[str, Any]],
        additional_instructions_provider: Callable[[str], str] | None = None,
        code_decision_engine: CodeDecisionEngine | None = None,
        llm_decision_engine: LLMDecisionEngine | None = None,
        owns_llm_engine: bool = False,
    ) -> None:
        self.world = world
        self.framework_name = framework_name
        self.implementation = implementation
        self.framework = framework
        self.framework_settings_provider = framework_settings_provider
        self.additional_instructions_provider = (
            additional_instructions_provider or (lambda _name: "")
        )
        self.code_decision_engine = code_decision_engine or CodeDecisionEngine()
        self.llm_decision_engine = llm_decision_engine
        self.owns_llm_engine = owns_llm_engine
        self.phase = DRIVING
        self.decision_sequence = 0
        self.pending_world_context: DetectedIncident | None = None
        self.last_decision: EthicalDecision | None = None
        self.finished = False

    @property
    def is_waiting_for_llm(self) -> bool:
        return self.phase == WAITING_FOR_LLM

    def configure(
        self,
        *,
        framework_name: str,
        implementation: str,
        framework: EthicalFramework,
    ) -> None:
        self.cancel_pending_decision()
        self.framework_name = framework_name
        self.implementation = implementation
        self.framework = framework
        self.last_decision = None

    def reset(self, *, reset_framework: bool = True) -> None:
        self.cancel_pending_decision()
        self.decision_sequence = 0
        self.last_decision = None
        self.finished = False
        if reset_framework:
            self.framework.reset()

    def cancel_pending_decision(self) -> None:
        if self.llm_decision_engine is not None:
            self.llm_decision_engine.cancel()
        self.pending_world_context = None
        self.phase = DRIVING

    def step(self, delta_time: float) -> SimulationStepResult:
        """Advance one tick; virtual time pauses while an LLM call is pending."""
        if self.finished:
            return SimulationStepResult(True)

        if self.phase == WAITING_FOR_LLM:
            event = self._poll_llm_decision()
            return SimulationStepResult(False, event)

        decision_event = None
        if self.phase == DRIVING:
            decision_event = self._trigger_decision_if_needed()
            if self.phase == WAITING_FOR_LLM:
                return SimulationStepResult(False)

        reached_tunnel = self.world.update(max(0.0, float(delta_time)))
        car = self.world.primary_car
        if self.phase == EXECUTING_DECISION and (
            car is None or not car.is_changing_lane
        ):
            self.phase = DRIVING
        self.finished = reached_tunnel
        return SimulationStepResult(reached_tunnel, decision_event)

    def _decision_context(self, incident: DetectedIncident) -> DecisionContext:
        car = self.world.primary_car
        return DecisionContext.from_state(
            decision_id=self.decision_sequence + 1,
            vehicle_position=car.x if car is not None else 0.0,
            state=incident.state,
            lane_changes_remaining=self.world.lane_changes_remaining,
        )

    def _trigger_decision_if_needed(self) -> SimulationDecisionEvent | None:
        incident = self.world.next_decision_context()
        if incident is None:
            return None
        context = self._decision_context(incident)

        if self.implementation == LLM_MODE:
            if self.llm_decision_engine is None:
                return self._apply_decision(
                    incident,
                    context,
                    self._llm_start_fallback("LLM decision engine is unavailable"),
                    llm_request="Unable to build the LLM request.",
                    llm_response="ERROR: LLM decision engine is unavailable",
                    llm_raw_response=(
                        "ERROR: LLM decision engine is unavailable"
                    ),
                )
            try:
                started = self.llm_decision_engine.submit(
                    framework_name=self.framework_name,
                    framework_settings=self.framework_settings_provider(
                        self.framework_name
                    ),
                    additional_instructions=self.additional_instructions_provider(
                        self.framework_name
                    ),
                    context=context,
                )
            except Exception as error:
                message = safe_error_message(error)
                return self._apply_decision(
                    incident,
                    context,
                    self._llm_start_fallback(message),
                    llm_request=(
                        f"Unable to build {self.framework_name} LLM request."
                    ),
                    llm_response=f"ERROR: {message}",
                    llm_raw_response=f"ERROR: {message}",
                )
            if started:
                self.pending_world_context = incident
                self.phase = WAITING_FOR_LLM
            return None

        decision = self.code_decision_engine.decide(self.framework, context)
        return self._apply_decision(incident, context, decision)

    def _llm_start_fallback(self, error: str) -> EthicalDecision:
        model = (
            self.llm_decision_engine.model_name
            if self.llm_decision_engine is not None
            else "Unknown"
        )
        return EthicalDecision(
            STAY,
            f"LLM Agent could not start: {error}. Safe fallback selected STAY.",
            {
                "mode": LLM_MODE,
                "model": model,
                "latency_ms": 0,
                "fallback": True,
                "attempts": 0,
                "llm_error": error,
            },
        )

    def _poll_llm_decision(self) -> SimulationDecisionEvent | None:
        if self.llm_decision_engine is None:
            self.phase = DRIVING
            return None
        result = self.llm_decision_engine.poll()
        if result is None:
            return None
        incident = self.pending_world_context
        self.pending_world_context = None
        if incident is None:
            self.phase = DRIVING
            return None
        resolved_decision = self.framework.resolve_llm_decision(
            result.decision,
            context=result.context,
        )
        return self._apply_decision(
            incident,
            result.context,
            resolved_decision,
            llm_request=result.llm_request,
            llm_response=result.llm_response,
            llm_raw_response=result.llm_raw_response,
        )

    def _apply_decision(
        self,
        incident: DetectedIncident,
        context: DecisionContext,
        decision: EthicalDecision,
        *,
        llm_request: str | None = None,
        llm_response: str | None = None,
        llm_raw_response: str | None = None,
    ) -> SimulationDecisionEvent:
        if decision.action not in {STAY, CHANGE_LANE}:
            decision = EthicalDecision(
                STAY,
                "Invalid decision action; safe fallback selected STAY.",
                {**decision.details, "fallback": True},
            )

        applied = decision
        lane_change_started = False
        if decision.action == CHANGE_LANE:
            lane_change_started = self.world.request_lane_change()
            if not lane_change_started:
                applied = EthicalDecision(
                    STAY,
                    decision.reason,
                    {
                        **decision.details,
                        "recommended_action": decision.action,
                        "lane_change_blocked": True,
                    },
                )

        self.world.mark_decision_handled(incident)
        self.decision_sequence = context.decision_id
        self.framework.record_decision(applied, context=context)
        self.last_decision = applied
        self.phase = EXECUTING_DECISION if lane_change_started else DRIVING
        return SimulationDecisionEvent(
            framework_name=self.framework_name,
            implementation=self.implementation,
            context=context,
            recommended_decision=decision,
            applied_decision=applied,
            lane_change_started=lane_change_started,
            llm_request=llm_request,
            llm_response=llm_response,
            llm_raw_response=llm_raw_response,
        )

    def close(self) -> None:
        self.cancel_pending_decision()
        if self.owns_llm_engine and self.llm_decision_engine is not None:
            self.llm_decision_engine.close()
