"""Factories for creating isolated ethical-framework instances."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from .base import EthicalFramework
from .catalog import CONSTANT, KANT, UTILITARIANISM, VIRTUE_ETHICS
from .constant import UTILITARIAN_EVALUATION, ConstantFramework
from .kant import KantFramework
from .rules import DEFAULT_RULE_ENABLED, DEFAULT_RULE_ORDER
from .utilitarian import DEFAULT_ENTITIES_VALUES, UtilitarianFramework
from .virtue import VirtueEthicsFramework


def create_ethical_framework(
    framework_name: str,
    framework_settings: Mapping[str, Any] | None = None,
    *,
    utilitarian_values: Mapping[str, float] | None = None,
) -> EthicalFramework:
    """Create fresh framework state for one interactive or automated run."""
    settings = deepcopy(dict(framework_settings or {}))
    shared_values = dict(utilitarian_values or DEFAULT_ENTITIES_VALUES)

    if framework_name == UTILITARIANISM:
        values = settings.get("entity_values", settings) or shared_values
        return UtilitarianFramework(dict(values))
    if framework_name == KANT:
        return KantFramework(
            rule_order=settings.get("rule_order", DEFAULT_RULE_ORDER),
            enabled_rules=settings.get("enabled_rules", DEFAULT_RULE_ENABLED),
        )
    if framework_name == CONSTANT:
        return ConstantFramework(
            enabled_rules=settings.get("enabled_rules", DEFAULT_RULE_ENABLED),
            conflict_resolution=settings.get(
                "conflict_resolution",
                UTILITARIAN_EVALUATION,
            ),
            entity_values=settings.get("entity_values", shared_values),
        )
    if framework_name == VIRTUE_ETHICS:
        return VirtueEthicsFramework()
    raise ValueError(f"Unknown ethical framework: {framework_name}")
