"""Shared moral-rule catalog and context-only rule evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from ..base import CHANGE_LANE, STAY, DecisionContext


DO_NOT_REDIRECT_HARM = "do_not_redirect_harm"
DO_NOT_USE_AS_MEANS = "do_not_use_as_means"
IGNORE_PERSONAL_CATEGORIES = "ignore_personal_categories"
IGNORE_NUMERICAL_DIFFERENCES = "ignore_numerical_differences"
PREFER_STAY_WHEN_UNRESOLVED = "prefer_stay_when_unresolved"


@dataclass(frozen=True)
class MoralRule:
    """Metadata for one configurable moral rule."""

    key: str
    label: str


MORAL_RULES = {
    DO_NOT_REDIRECT_HARM: MoralRule(
        DO_NOT_REDIRECT_HARM,
        "Do not intentionally redirect harm",
    ),
    DO_NOT_USE_AS_MEANS: MoralRule(
        DO_NOT_USE_AS_MEANS,
        "Do not use a person merely as a means",
    ),
    IGNORE_PERSONAL_CATEGORIES: MoralRule(
        IGNORE_PERSONAL_CATEGORIES,
        "Ignore personal categories",
    ),
    IGNORE_NUMERICAL_DIFFERENCES: MoralRule(
        IGNORE_NUMERICAL_DIFFERENCES,
        "Ignore numerical differences between lives",
    ),
    PREFER_STAY_WHEN_UNRESOLVED: MoralRule(
        PREFER_STAY_WHEN_UNRESOLVED,
        "Prefer STAY when unresolved",
    ),
}

DEFAULT_RULE_ORDER = tuple(MORAL_RULES)
DEFAULT_RULE_ENABLED = {rule_key: True for rule_key in DEFAULT_RULE_ORDER}


def normalize_rule_order(rule_order: list[str] | tuple[str, ...]) -> list[str]:
    """Keep known unique rules and append any missing catalog entries."""
    normalized: list[str] = []
    for rule_key in rule_order:
        if rule_key in MORAL_RULES and rule_key not in normalized:
            normalized.append(rule_key)
    normalized.extend(
        rule_key for rule_key in DEFAULT_RULE_ORDER if rule_key not in normalized
    )
    return normalized


def normalize_enabled_rules(enabled_rules: dict[str, bool]) -> dict[str, bool]:
    """Return a complete boolean state for the shared rule catalog."""
    return {
        rule_key: bool(enabled_rules.get(rule_key, True))
        for rule_key in DEFAULT_RULE_ORDER
    }


def evaluate_rule(rule_key: str, context: DecisionContext) -> str | None:
    """Evaluate one rule without accessing anything outside vehicle perception."""
    current_entities = context.current_lane_entities
    other_entities = context.other_lane_entities
    current_count = len(current_entities)
    other_count = len(other_entities)

    if rule_key in {DO_NOT_REDIRECT_HARM, DO_NOT_USE_AS_MEANS}:
        if other_count:
            return STAY
        return CHANGE_LANE if current_count else None

    if rule_key == IGNORE_PERSONAL_CATEGORIES:
        if other_count < current_count:
            return CHANGE_LANE
        if current_count < other_count:
            return STAY
        return None

    if rule_key == IGNORE_NUMERICAL_DIFFERENCES:
        if current_count and other_count:
            return STAY
        if current_count:
            return CHANGE_LANE
        return STAY

    if rule_key == PREFER_STAY_WHEN_UNRESOLVED:
        return STAY

    return None
