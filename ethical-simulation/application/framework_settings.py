"""Framework-settings navigation and state synchronization."""

from __future__ import annotations

import math

import arcade
import arcade.gui

from decision_engine import CODE_MODE, LLM_MODE
from ethics.constant import CONFLICT_RESOLVERS, ConstantFramework
from ethics.kant import KantFramework
from ethics.utils.config import (
    CONSTANT,
    DEFAULT_CONSTANT_RULE_ORDER,
    FRAMEWORK_IMPLEMENTATIONS,
    FRAMEWORKS,
    KANT,
    LLM_FRAMEWORKS,
    UTILITARIANISM,
)
from ethics.utils.rules import MORAL_RULES
from ui.screens import build_framework_settings, build_menu


class FrameworkSettingsMixin:
    """Connect framework configuration screens to ethical strategies."""

    def _open_menu(self, _event: arcade.gui.UIOnClickEvent | None = None) -> None:
        self._pause(None)
        self.active_screen = "menu"
        self.manager.clear()
        build_menu(
            self.manager,
            on_framework=self._open_framework_settings,
            on_scenario=self._open_scenario_settings,
            on_general=self._open_general_settings,
            on_info=self._open_info,
            on_back=self._return_to_simulation,
        )

    def _return_to_simulation(
        self, _event: arcade.gui.UIOnClickEvent | None = None
    ) -> None:
        self.active_screen = "simulation"
        self.manager.clear()
        self._setup_toolbar()

    def _open_framework_settings(
        self, _event: arcade.gui.UIOnClickEvent | None = None
    ) -> None:
        selected = (
            self.current_framework
            if self.current_framework in FRAMEWORKS
            else UTILITARIANISM
        )
        self.framework_editor_mode = (
            self.current_implementation if selected in LLM_FRAMEWORKS else CODE_MODE
        )
        self._show_framework_editor(selected)

    def _show_framework_editor(self, framework_name: str) -> None:
        self.active_screen = "framework_settings"
        self.framework_editor_framework = framework_name
        allowed_implementations = FRAMEWORK_IMPLEMENTATIONS.get(
            framework_name,
            (CODE_MODE,),
        )
        if self.framework_editor_mode not in allowed_implementations:
            self.framework_editor_mode = allowed_implementations[0]
        self.manager.clear()
        (
            self.utilitarian_entity_inputs,
            self.llm_additional_instructions_input,
            self.framework_status_label,
        ) = build_framework_settings(
            self.manager,
            selected=framework_name,
            selected_mode=self.framework_editor_mode,
            utilitarian_entity_values=self.framework_settings[UTILITARIANISM],
            kant_rules=self._framework_rule_rows(KANT),
            constant_rules=self._framework_rule_rows(CONSTANT),
            constant_conflict_resolution=self.framework_settings[CONSTANT][
                "conflict_resolution"
            ],
            conflict_resolvers=list(CONFLICT_RESOLVERS),
            llm_additional_instructions=self.llm_additional_instructions.get(
                framework_name,
                "",
            ),
            llm_model=self.llm_decision_engine.model_name,
            on_select=self._show_framework_editor,
            on_select_mode=self._set_framework_editor_mode,
            on_save=self._save_utilitarian_settings,
            on_save_llm=self._save_llm_instructions,
            on_toggle_rule=self._toggle_framework_rule,
            on_move_kant_rule=self._move_kant_rule,
            on_constant_resolver=self._set_constant_conflict_resolver,
            on_back=self._open_menu,
        )

    def _set_framework_editor_mode(self, implementation: str) -> None:
        if implementation not in {CODE_MODE, LLM_MODE}:
            return
        framework_name = getattr(
            self,
            "framework_editor_framework",
            self.current_framework,
        )
        if implementation not in FRAMEWORK_IMPLEMENTATIONS.get(framework_name, ()):
            return
        self.framework_editor_mode = implementation
        self._show_framework_editor(framework_name)

    def _save_llm_instructions(
        self,
        _event: arcade.gui.UIOnClickEvent | None = None,
    ) -> None:
        framework_name = getattr(
            self,
            "framework_editor_framework",
            self.current_framework,
        )
        if (
            framework_name not in LLM_FRAMEWORKS
            or self.llm_additional_instructions_input is None
        ):
            return
        self.llm_additional_instructions[framework_name] = (
            self.llm_additional_instructions_input.text.strip()
        )
        if self.framework_status_label is not None:
            self.framework_status_label.text = (
                "Additional Instructions saved in application state."
            )
            self.framework_status_label.update_font(font_color=(74, 222, 128))

    def _framework_rule_rows(
        self,
        framework_name: str,
    ) -> list[tuple[str, str, bool]]:
        settings = self.framework_settings[framework_name]
        rule_order = (
            settings["rule_order"]
            if framework_name == KANT
            else list(DEFAULT_CONSTANT_RULE_ORDER)
        )
        enabled_rules = settings["enabled_rules"]
        return [
            (
                rule_key,
                MORAL_RULES[rule_key].label,
                bool(enabled_rules[rule_key]),
            )
            for rule_key in rule_order
        ]

    def _toggle_framework_rule(
        self,
        framework_name: str,
        rule_key: str,
    ) -> None:
        settings = self.framework_settings[framework_name]
        enabled_rules = settings["enabled_rules"]
        enabled_rules[rule_key] = not enabled_rules[rule_key]
        self._apply_framework_rule_settings(framework_name)
        self._show_framework_editor(framework_name)

    def _move_kant_rule(self, rule_key: str, direction: int) -> None:
        rule_order = self.framework_settings[KANT]["rule_order"]
        current_index = rule_order.index(rule_key)
        target_index = max(0, min(len(rule_order) - 1, current_index + direction))
        if target_index == current_index:
            return
        rule_order[current_index], rule_order[target_index] = (
            rule_order[target_index],
            rule_order[current_index],
        )
        self._apply_framework_rule_settings(KANT)
        self._show_framework_editor(KANT)

    def _set_constant_conflict_resolver(self, resolver: str) -> None:
        self.framework_settings[CONSTANT]["conflict_resolution"] = resolver
        self._apply_framework_rule_settings(CONSTANT)
        self._show_framework_editor(CONSTANT)

    def _apply_framework_rule_settings(self, framework_name: str) -> None:
        settings = self.framework_settings[framework_name]
        framework = self.ethical_frameworks[framework_name]
        if isinstance(framework, KantFramework):
            framework.configure_rules(
                settings["rule_order"],
                settings["enabled_rules"],
            )
        elif isinstance(framework, ConstantFramework):
            framework.configure_rules(
                settings["enabled_rules"],
                settings["conflict_resolution"],
            )

    def _save_utilitarian_settings(
        self, _event: arcade.gui.UIOnClickEvent | None = None
    ) -> None:
        parsed_values: dict[str, float] = {}
        has_error = False
        for entity_model, input_widget in self.utilitarian_entity_inputs.items():
            try:
                value = float(input_widget.text.strip())
                if not math.isfinite(value):
                    raise ValueError
            except ValueError:
                input_widget.invalid = True
                has_error = True
            else:
                input_widget.invalid = False
                parsed_values[entity_model] = value

        if self.framework_status_label is None:
            return
        if has_error:
            self.framework_status_label.text = (
                "Enter a valid numeric value in every field."
            )
            return

        self.framework_settings[UTILITARIANISM].update(parsed_values)
        utilitarian = self.ethical_frameworks[UTILITARIANISM]
        utilitarian.update_entity_values(parsed_values)
        constant = self.ethical_frameworks[CONSTANT]
        constant.update_entity_values(parsed_values)
        self.framework_status_label.text = "Values saved in simulation state."
