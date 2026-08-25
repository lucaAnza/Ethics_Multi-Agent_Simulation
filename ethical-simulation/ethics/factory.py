"""Factory Method implementations for isolated ethical frameworks."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from .base import EthicalFramework
from .config import (
    CONSTANT,
    DEFAULT_ENTITIES_VALUES,
    KANT,
    UTILITARIANISM,
    VIRTUE_ETHICS,
)
from .constant import UTILITARIAN_EVALUATION, ConstantFramework
from .kant import KantFramework
from .rules import DEFAULT_RULE_ENABLED, DEFAULT_RULE_ORDER
from .utilitarian import UtilitarianFramework
from .virtue import VirtueEthicsFramework


class EthicalFrameworkCreator(ABC):
    """Creator interface implemented once for every ethical framework."""

    @abstractmethod
    def create(
        self,
        settings: Mapping[str, Any],
        utilitarian_values: Mapping[str, float],
    ) -> EthicalFramework:
        """Return a new framework instance without shared runtime state."""


class UtilitarianFrameworkCreator(EthicalFrameworkCreator):
    def create(
        self,
        settings: Mapping[str, Any],
        utilitarian_values: Mapping[str, float],
    ) -> EthicalFramework:
        values = settings.get("entity_values", settings) or utilitarian_values
        return UtilitarianFramework(dict(values))


class KantFrameworkCreator(EthicalFrameworkCreator):
    def create(
        self,
        settings: Mapping[str, Any],
        _utilitarian_values: Mapping[str, float],
    ) -> EthicalFramework:
        return KantFramework(
            rule_order=settings.get("rule_order", DEFAULT_RULE_ORDER),
            enabled_rules=settings.get("enabled_rules", DEFAULT_RULE_ENABLED),
        )


class ConstantFrameworkCreator(EthicalFrameworkCreator):
    def create(
        self,
        settings: Mapping[str, Any],
        utilitarian_values: Mapping[str, float],
    ) -> EthicalFramework:
        return ConstantFramework(
            enabled_rules=settings.get("enabled_rules", DEFAULT_RULE_ENABLED),
            conflict_resolution=settings.get(
                "conflict_resolution",
                UTILITARIAN_EVALUATION,
            ),
            entity_values=settings.get("entity_values", utilitarian_values),
        )


class VirtueEthicsFrameworkCreator(EthicalFrameworkCreator):
    def create(
        self,
        _settings: Mapping[str, Any],
        _utilitarian_values: Mapping[str, float],
    ) -> EthicalFramework:
        return VirtueEthicsFramework()


class EthicalFrameworkFactory:
    """Select the appropriate creator and delegate framework construction."""

    _creators: dict[str, EthicalFrameworkCreator] = {
        UTILITARIANISM: UtilitarianFrameworkCreator(),
        KANT: KantFrameworkCreator(),
        CONSTANT: ConstantFrameworkCreator(),
        VIRTUE_ETHICS: VirtueEthicsFrameworkCreator(),
    }

    @classmethod
    def create(
        cls,
        framework_name: str,
        framework_settings: Mapping[str, Any] | None = None,
        *,
        utilitarian_values: Mapping[str, float] | None = None,
    ) -> EthicalFramework:
        """Create fresh framework state for one interactive or automated run."""
        creator = cls._creators.get(framework_name)
        if creator is None:
            raise ValueError(f"Unknown ethical framework: {framework_name}")

        settings = deepcopy(dict(framework_settings or {}))
        shared_values = deepcopy(
            dict(utilitarian_values or DEFAULT_ENTITIES_VALUES)
        )
        return creator.create(settings, shared_values)


def create_ethical_framework(
    framework_name: str,
    framework_settings: Mapping[str, Any] | None = None,
    *,
    utilitarian_values: Mapping[str, float] | None = None,
) -> EthicalFramework:
    """Compatibility wrapper around :class:`EthicalFrameworkFactory`."""
    return EthicalFrameworkFactory.create(
        framework_name,
        framework_settings,
        utilitarian_values=utilitarian_values,
    )
