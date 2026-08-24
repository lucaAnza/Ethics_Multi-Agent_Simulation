"""Constant framework using equal rules and an explicit conflict resolver."""

from __future__ import annotations

from collections.abc import Mapping

from .base import STAY, EthicalDecision, EthicalFramework, EntitySnapshot, PerceptionState
from .evaluation import choose_lower_cost
from .rules import (
    DEFAULT_RULE_ENABLED,
    DEFAULT_RULE_ORDER,
    evaluate_rule,
    normalize_enabled_rules,
)
from .utilitarian import DEFAULT_ENTITIES_VALUES


UTILITARIAN_EVALUATION = "Utilitarian evaluation"
CONFLICT_RESOLVERS = (UTILITARIAN_EVALUATION,)


class ConstantFramework(EthicalFramework):
    """Evaluate every enabled moral rule at the same level."""

    def __init__(
        self,
        enabled_rules: dict[str, bool] | None = None,
        conflict_resolution: str = UTILITARIAN_EVALUATION,
        entity_values: Mapping[str, float] | None = None,
    ) -> None:
        self.enabled_rules = normalize_enabled_rules(
            enabled_rules or DEFAULT_RULE_ENABLED
        )
        self.conflict_resolution = self._normalize_resolver(conflict_resolution)
        self.entity_values = dict(entity_values or DEFAULT_ENTITIES_VALUES)
        self.decision_history: list[list[str]] = []
        self.moral_conflicts = 0

    @staticmethod
    def _normalize_resolver(resolver: str) -> str:
        return resolver if resolver in CONFLICT_RESOLVERS else UTILITARIAN_EVALUATION

    def configure_rules(
        self,
        enabled_rules: dict[str, bool],
        conflict_resolution: str,
    ) -> None:
        """Replace rule switches and resolver without affecting history."""
        self.enabled_rules = normalize_enabled_rules(enabled_rules)
        self.conflict_resolution = self._normalize_resolver(conflict_resolution)

    def update_entity_values(self, values: Mapping[str, float]) -> None:
        """Keep the utilitarian conflict resolver aligned with shared values."""
        self.entity_values.update(values)

    def decide(self, state: PerceptionState) -> EthicalDecision:
        votes = [
            action
            for rule_key in DEFAULT_RULE_ORDER
            if self.enabled_rules[rule_key]
            if (action := evaluate_rule(rule_key, state)) is not None
        ]
        if not votes:
            return EthicalDecision(
                STAY,
                "No enabled moral rule resolved the situation; defaulting to STAY.",
            )

        distinct_actions = set(votes)
        if len(distinct_actions) == 1:
            action = votes[0]
            return EthicalDecision(
                action,
                f"All applicable moral rules selected {action}.",
            )

        current_entities = state.get("current_lane_entities", [])
        other_entities = state.get("other_lane_entities", [])
        action, current_cost, other_cost = choose_lower_cost(
            current_entities,
            other_entities,
            self.entity_values,
        )
        if current_cost == other_cost:
            reason = (
                "Moral rules conflicted. Utilitarian evaluation was tied, "
                "so STAY was selected."
            )
        else:
            reason = (
                "Moral rules conflicted. Utilitarian evaluation selected "
                "the lower malus."
            )
        return EthicalDecision(action, reason)

    def record_decision(self, decision: EthicalDecision) -> None:
        self.decision_history.append([decision.action, decision.reason])
        if decision.reason.startswith("Moral rules conflicted."):
            self.moral_conflicts += 1

    def reset(self) -> None:
        self.decision_history.clear()
        self.moral_conflicts = 0

    def summary(
        self,
        casualties: list[EntitySnapshot],
    ) -> list[tuple[str, str]]:
        return [
            ("Decisions", str(len(self.decision_history))),
            ("Moral conflicts", str(self.moral_conflicts)),
            ("Conflict resolver", self.conflict_resolution),
        ]
