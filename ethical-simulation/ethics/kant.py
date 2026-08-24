"""Kantian framework using configurable rules with strict priority."""

from __future__ import annotations

from .base import STAY, DecisionContext, EthicalDecision, EthicalFramework, EntitySnapshot
from .rules import (
    DEFAULT_RULE_ENABLED,
    DEFAULT_RULE_ORDER,
    MORAL_RULES,
    evaluate_rule,
    normalize_enabled_rules,
    normalize_rule_order,
)


class KantFramework(EthicalFramework):
    """Apply the first applicable enabled rule in the configured hierarchy."""

    def __init__(
        self,
        rule_order: list[str] | tuple[str, ...] = DEFAULT_RULE_ORDER,
        enabled_rules: dict[str, bool] | None = None,
    ) -> None:
        super().__init__()
        self.rule_order = normalize_rule_order(rule_order)
        self.enabled_rules = normalize_enabled_rules(
            enabled_rules or DEFAULT_RULE_ENABLED
        )

    def configure_rules(
        self,
        rule_order: list[str],
        enabled_rules: dict[str, bool],
    ) -> None:
        """Replace the hierarchy and enabled state without affecting history."""
        self.rule_order = normalize_rule_order(rule_order)
        self.enabled_rules = normalize_enabled_rules(enabled_rules)

    def decide(self, context: DecisionContext) -> EthicalDecision:
        for rule_key in self.rule_order:
            if not self.enabled_rules[rule_key]:
                continue
            action = evaluate_rule(rule_key, context)
            if action is None:
                continue
            rule_label = MORAL_RULES[rule_key].label
            return EthicalDecision(
                action,
                f'"{rule_label}" has higher priority.',
                {
                    "deciding_rule": rule_label,
                    "rule_key": rule_key,
                },
            )

        return EthicalDecision(
            STAY,
            "No enabled rule resolved the situation; defaulting to STAY.",
        )

    def summary(
        self,
        casualties: list[EntitySnapshot],
    ) -> list[tuple[str, str]]:
        return [
            ("Decisions", str(len(self.decision_history))),
            ("Active rules", str(sum(self.enabled_rules.values()))),
        ]
