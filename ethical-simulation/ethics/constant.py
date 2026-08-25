"""Constant framework using equal rules and an explicit conflict resolver."""

from __future__ import annotations

from collections.abc import Mapping

from .base import STAY, DecisionContext, EthicalDecision, EthicalFramework, EntitySnapshot
from .config import DEFAULT_ENTITIES_VALUES
from .evaluation import choose_lower_cost
from .rules import (
    DEFAULT_RULE_ENABLED,
    DEFAULT_RULE_ORDER,
    evaluate_rule,
    normalize_enabled_rules,
)


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
        super().__init__()
        self.enabled_rules = normalize_enabled_rules(
            enabled_rules or DEFAULT_RULE_ENABLED
        )
        self.conflict_resolution = self._normalize_resolver(conflict_resolution)
        self.entity_values = dict(entity_values or DEFAULT_ENTITIES_VALUES)
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

    def decide(self, context: DecisionContext) -> EthicalDecision:
        votes = [
            (rule_key, action)
            for rule_key in DEFAULT_RULE_ORDER
            if self.enabled_rules[rule_key]
            if (action := evaluate_rule(rule_key, context)) is not None
        ]
        if not votes:
            return EthicalDecision(
                STAY,
                "No enabled moral rule resolved the situation; defaulting to STAY.",
            )

        distinct_actions = {action for _rule_key, action in votes}
        if len(distinct_actions) == 1:
            action = votes[0][1]
            return EthicalDecision(
                action,
                f"All applicable moral rules selected {action}.",
                {
                    "rule_outcome": "Unanimous",
                    "supporting_rules": [
                        rule_key for rule_key, _action in votes
                    ],
                },
            )

        current_entities = list(context.current_lane_entities)
        other_entities = list(context.other_lane_entities)
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
        return EthicalDecision(
            action,
            reason,
            {
                "moral_conflict": True,
                "conflict_resolver": self.conflict_resolution,
                "current_lane_malus": current_cost,
                "other_lane_malus": other_cost,
            },
        )

    def record_decision(
        self,
        decision: EthicalDecision,
        *,
        context: DecisionContext,
    ) -> None:
        super().record_decision(
            decision,
            context=context,
        )
        if decision.details.get("moral_conflict"):
            self.moral_conflicts += 1

    def reset(self) -> None:
        super().reset()
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
