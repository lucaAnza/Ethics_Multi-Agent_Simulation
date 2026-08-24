"""Compose deterministic prompts without coupling them to Gemini."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import yaml

from ethics.base import DecisionContext
from .schemas import PromptPackage


PROMPT_FILENAMES = {
    "Utilitarianism": "utilitarianism.yaml",
    "Kant": "kant.yaml",
    "Constant": "constant.yaml",
    "Virtue Ethics": "virtue_ethics.yaml",
}


class PromptBuilder:
    """Load hidden base prompts and append settings, instructions, and context."""

    def __init__(self, prompts_dir: Path | None = None) -> None:
        self.prompts_dir = prompts_dir or (
            Path(__file__).resolve().parents[1] / "config" / "prompts"
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
        prompt = "\n\n".join(
            (
                "FRAMEWORK PROMPT\n" + framework_prompt,
                "STRUCTURED FRAMEWORK SETTINGS\n"
                + json.dumps(framework_settings, indent=2, sort_keys=True),
                "USER ADDITIONAL INSTRUCTIONS\n" + custom,
                "CURRENT DECISION CONTEXT\n"
                + json.dumps(context.as_payload(), indent=2, sort_keys=True),
            )
        )
        return PromptPackage(system_instruction=self._common, prompt=prompt)
