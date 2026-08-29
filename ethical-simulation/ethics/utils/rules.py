"""Shared moral-rule catalog and context-only rule evaluation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from ..base import CHANGE_LANE, STAY, DecisionContext
from simulation.entities import pedestrian_category



########## RULES DEFINITION AND EVALUATION ##########
RuleEvaluator = Callable[[DecisionContext], str | None]
@dataclass(frozen=True)
class MoralRule:
    key: str
    label: str
    evaluator: RuleEvaluator


def _do_not_redirect_harm(context: DecisionContext) -> str | None:
    current_count = len(context.current_lane_entities)
    other_count = len(context.other_lane_entities)

    if other_count:
        return STAY

    return CHANGE_LANE if current_count else None


def _ignore_personal_categories(context: DecisionContext) -> str | None:
    current_count = len(context.current_lane_entities)
    other_count = len(context.other_lane_entities)

    if other_count < current_count:
        return CHANGE_LANE

    if current_count < other_count:
        return STAY

    return None


def _ignore_numerical_differences(context: DecisionContext) -> str | None:
    current_count = len(context.current_lane_entities)
    other_count = len(context.other_lane_entities)

    if current_count and other_count:
        return STAY

    if current_count:
        return CHANGE_LANE

    return STAY

def _do_not_increase_harm(context: DecisionContext) -> str | None:
    current_count = len(context.current_lane_entities)
    other_count = len(context.other_lane_entities)

    if other_count > current_count:
        return STAY

    return None

def _always_protect_child(context: DecisionContext) -> str | None:
    current_children = sum(
        1
        for entity in context.current_lane_entities
        if pedestrian_category(str(entity.get("model", ""))) == "Child"
    )

    other_children = sum(
        1
        for entity in context.other_lane_entities
        if pedestrian_category(str(entity.get("model", ""))) == "Child"
    )

    # Child only in current lane -> move away from the child
    if current_children > 0 and other_children == 0:
        return CHANGE_LANE

    # Child only in other lane -> stay in current lane
    if other_children > 0 and current_children == 0:
        return STAY

    # Children in both lanes, or no children:
    # this rule alone cannot determine the action
    return None

def _prefer_stay_when_unresolved(context: DecisionContext) -> str | None:
    return STAY


MORAL_RULES = {
    rule.key: rule
    for rule in (
        MoralRule(
            key="do_not_redirect_harm",
            label="Do not intentionally redirect harm",
            evaluator=_do_not_redirect_harm,
        ),
        MoralRule(
            key="ignore_personal_categories",
            label="Ignore personal categories",
            evaluator=_ignore_personal_categories,
        ),
        MoralRule(
            key="ignore_numerical_differences",
            label="Ignore numerical differences between lives",
            evaluator=_ignore_numerical_differences,
        ),
        MoralRule(
            key="prefer_stay_when_unresolved",
            label="Prefer STAY when unresolved",
            evaluator=_prefer_stay_when_unresolved,
        ),
        MoralRule(
            key="do_not_increase_harm",
            label="Do not increase harm",
            evaluator=_do_not_increase_harm,
        ),
        MoralRule(
            key="always_protect_child",
            label="Always protect children",
            evaluator=_always_protect_child,
        ),
    )
}
# ###################################################à


DEFAULT_RULE_ORDER = tuple(MORAL_RULES)
DEFAULT_RULE_ENABLED = {
    rule_key: True
    for rule_key in DEFAULT_RULE_ORDER
}


def normalize_rule_order(
    rule_order: list[str] | tuple[str, ...],
) -> list[str]:
    normalized: list[str] = []

    for rule_key in rule_order:
        if rule_key in MORAL_RULES and rule_key not in normalized:
            normalized.append(rule_key)

    normalized.extend(
        rule_key
        for rule_key in DEFAULT_RULE_ORDER
        if rule_key not in normalized
    )

    return normalized


def normalize_enabled_rules(
    enabled_rules: dict[str, bool],
) -> dict[str, bool]:
    return {
        rule_key: bool(enabled_rules.get(rule_key, True))
        for rule_key in DEFAULT_RULE_ORDER
    }


def evaluate_rule(
    rule_key: str,
    context: DecisionContext,
) -> str | None:
    rule = MORAL_RULES.get(rule_key)

    if rule is None:
        return None

    return rule.evaluator(context)
