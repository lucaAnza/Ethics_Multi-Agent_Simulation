"""Compose deterministic prompts without coupling them to Gemini."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import yaml

from ethics.base import CHANGE_LANE, MORAL_CONFLICT, STAY, DecisionContext
from ethics.utils.config import (
    CONSTANT,
    DEFAULT_KANT_RULE_ENABLED,
    DEFAULT_KANT_RULE_ORDER,
    KANT,
)
from ethics.utils.rules import (
    MORAL_RULES,
    normalize_enabled_rules,
    normalize_rule_order,
)
from .config import PROMPT_FILENAMES
from .schemas import PromptPackage


class PromptBuilder:
    """Load hidden base prompts and append settings, instructions, and context."""

    def __init__(self, prompts_dir: Path | None = None) -> None:
        self.prompts_dir = prompts_dir or (
            Path(__file__).resolve().parent / "promts"
        )
        self._common = self._load_prompt("common.yaml", "system_prompt")
        self._framework_prompts = {
            name: self._load_prompt(filename, "framework_prompt")
            for name, filename in PROMPT_FILENAMES.items()
        }

    def _load_prompt(self, filename: str, key: str) -> str:
        path = self.prompts_dir / filename
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as error:
            raise RuntimeError(f"Could not load prompt configuration: {path}") from error
        value = data.get(key) if isinstance(data, dict) else None
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(f"Prompt key {key!r} is missing from {path}")
        return value.strip()

    @staticmethod
    def _framework_settings_for_prompt(
        framework_name: str,
        framework_settings: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Return an LLM-friendly representation of framework settings."""
        settings = dict(framework_settings)
        if framework_name == CONSTANT:
            # Constant's LLM detects agreement or conflict only. Resolver data
            # stays local so the model cannot perform that second-stage choice.
            settings.pop("conflict_resolution", None)
            settings.pop("entity_values", None)
            settings["conflict_behavior"] = (
                "Return MORAL_CONFLICT when applicable rules select both "
                "STAY and CHANGE_LANE; do not resolve it."
            )
            return settings
        if framework_name != KANT:
            return settings

        configured_order = settings.pop(
            "rule_order",
            DEFAULT_KANT_RULE_ORDER,
        )
        if not isinstance(configured_order, (list, tuple)):
            configured_order = DEFAULT_KANT_RULE_ORDER
        rule_order = normalize_rule_order(configured_order)

        configured_enabled = settings.pop(
            "enabled_rules",
            DEFAULT_KANT_RULE_ENABLED,
        )
        if not isinstance(configured_enabled, Mapping):
            configured_enabled = DEFAULT_KANT_RULE_ENABLED
        enabled_rules = normalize_enabled_rules(
            dict(configured_enabled),
            DEFAULT_KANT_RULE_ENABLED,
        )

        settings["priority_convention"] = (
            "1 is the highest priority; larger numbers have lower priority."
        )
        settings["rules_by_priority"] = [
            {
                "priority": priority,
                "key": rule_key,
                "label": MORAL_RULES[rule_key].label,
                "enabled": enabled_rules[rule_key],
            }
            for priority, rule_key in enumerate(rule_order, start=1)
        ]
        return settings

    def build(
        self,
        *,
        framework_name: str,
        framework_settings: Mapping[str, Any],
        additional_instructions: str,
        context: DecisionContext,
    ) -> PromptPackage:
        try:
            framework_prompt = self._framework_prompts[framework_name]
        except KeyError as error:
            raise ValueError(
                f"LLM mode is not supported for {framework_name}"
            ) from error

        custom = additional_instructions.strip() or "No additional instructions."
        serialized_settings = self._framework_settings_for_prompt(
            framework_name,
            framework_settings,
        )
        prompt = "\n\n".join(
            (
                "FRAMEWORK PROMPT\n" + framework_prompt,
                "STRUCTURED FRAMEWORK SETTINGS\n"
                + json.dumps(serialized_settings, indent=2, sort_keys=True),
                "USER ADDITIONAL INSTRUCTIONS\n" + custom,
                "CURRENT DECISION CONTEXT\n"
                + json.dumps(context.as_payload(), indent=2, sort_keys=True),
            )
        )
        allowed_actions = (
            (STAY, CHANGE_LANE, MORAL_CONFLICT)
            if framework_name == CONSTANT
            else (STAY, CHANGE_LANE)
        )
        return PromptPackage(
            system_instruction=self._common,
            prompt=prompt,
            allowed_actions=allowed_actions,
        )
