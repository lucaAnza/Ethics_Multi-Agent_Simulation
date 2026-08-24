"""Builders for menu and settings screens.

The builders own layout only. Navigation and application state remain in the
window, which keeps the simulation independent from these widgets.
"""

from collections.abc import Callable
import math

import arcade
import arcade.gui

FRAMEWORK_NAMES = ["Utilitarianism", "Kant", "Constant", "Virtue Ethics"]

ENTITY_MODEL_LABELS = {
    "man": "Man",
    "woman": "Woman",
    "old_man": "Old man",
    "old_woman": "Old woman",
    "boy": "Boy",
    "girl": "Girl",
    "custom": "Custom",
}

PEDESTRIAN_ACTION_LABELS = {
    "still": "Still",
    "move_right": "Move right",
    "move_left": "Move left",
    "move_down": "Move down",
    "move_up": "Move up",
    "random_move": "Random move",
}

TEXT = (238, 243, 248)
MUTED = (155, 170, 185)

MEDAL_COLORS = (
    (212, 175, 55),   # Gold
    (192, 192, 192),  # Silver
    (205, 127, 50),   # Bronze
)

RANKED_ROW_COLORS = (
    (67, 56, 24, 210),
    (49, 56, 66, 210),
    (65, 43, 28, 210),
)

BUTTON_COLORS = {
    "default": ((51, 65, 85), (65, 81, 104), (38, 50, 68)),
    "framework": ((109, 40, 217), (124, 58, 237), (91, 33, 182)),
    "scenario": ((15, 118, 110), (13, 148, 136), (17, 94, 89)),
    "general": ((180, 83, 9), (217, 119, 6), (146, 64, 14)),
    "info": ((71, 85, 105), (100, 116, 139), (51, 65, 85)),
    "save": ((21, 128, 61), (22, 163, 74), (20, 101, 52)),
    "link": ((3, 105, 161), (2, 132, 199), (7, 89, 133)),
    # Back buttons always use #2563EB as their normal state.
    "back": ((37, 99, 235), (59, 130, 246), (29, 78, 216)),
    "selected": ((67, 56, 202), (79, 70, 229), (55, 48, 163)),
    "car": ((30, 88, 145), (37, 111, 181), (26, 70, 116)),
    "danger": ((153, 27, 27), (185, 28, 28), (127, 29, 29)),
}


class RankDot(arcade.gui.UIWidget):
    """Small geometric medal marker that does not rely on emoji fonts."""

    def __init__(self) -> None:
        super().__init__(width=18, height=36)
        self.medal_color: tuple[int, int, int] | None = None

    def set_medal_color(self, color: tuple[int, int, int] | None) -> None:
        self.medal_color = color
        self.trigger_render()

    def do_render(self, surface) -> None:
        if self.medal_color is None:
            return
        self.prepare_render(surface)
        center_x = self.content_width / 2
        center_y = self.content_height / 2
        arcade.draw_circle_filled(center_x, center_y, 6, self.medal_color, num_segments=24)
        arcade.draw_circle_outline(
            center_x,
            center_y,
            6,
            (240, 244, 248),
            1,
            num_segments=24,
        )


def _rank_entity_models(values: dict[str, float]) -> list[str]:
    """Rank models by descending value, preserving source order for ties."""
    return sorted(values, key=lambda model: -values[model])


def _button_style(variant: str) -> dict:
    normal, hover, pressed = BUTTON_COLORS[variant]
    style = arcade.gui.UIFlatButton.UIStyle
    return {
        "normal": style(bg=normal, font_color=TEXT),
        "hover": style(bg=hover, font_color=TEXT, border=(148, 163, 184), border_width=1),
        "press": style(bg=pressed, font_color=TEXT),
        "disabled": style(bg=(55, 65, 78), font_color=MUTED),
    }


def _button(
    text: str,
    handler: Callable,
    width: int = 340,
    *,
    variant: str = "default",
    height: int = 42,
) -> arcade.gui.UIFlatButton:
    button = arcade.gui.UIFlatButton(
        text=text,
        width=width,
        height=height,
        style=_button_style(variant),
    )
    button.on_click = handler
    return button


def _add_centered(manager: arcade.gui.UIManager, content: arcade.gui.UIWidget) -> None:
    anchor = arcade.gui.UIAnchorLayout()
    anchor.add(content, anchor_x="center", anchor_y="center")
    manager.add(anchor)


def _heading(title: str, subtitle: str, width: int) -> arcade.gui.UIBoxLayout:
    header = arcade.gui.UIBoxLayout(vertical=True, space_between=4)
    header.add(
        arcade.gui.UILabel(
            text=title,
            width=width,
            height=34,
            font_size=20,
            bold=True,
            text_color=TEXT,
        )
    )
    header.add(
        arcade.gui.UILabel(
            text=subtitle,
            width=width,
            height=24,
            font_size=10,
            text_color=MUTED,
        )
    )
    return header


def _section_heading(title: str, subtitle: str, width: int) -> arcade.gui.UIBoxLayout:
    """Compact centered heading used inside settings cards."""
    header = arcade.gui.UIBoxLayout(vertical=True, space_between=2)
    header.add(
        arcade.gui.UILabel(
            text=title,
            width=width,
            height=28,
            font_size=17,
            bold=True,
            text_color=TEXT,
            align="center",
        )
    )
    header.add(
        arcade.gui.UILabel(
            text=subtitle,
            width=width,
            height=18,
            font_size=8,
            text_color=MUTED,
            align="center",
        )
    )
    return header


def _section_card(
    content: arcade.gui.UIBoxLayout,
    *,
    width: int,
    height: int,
    accent: tuple[int, int, int],
) -> arcade.gui.UIAnchorLayout:
    """Wrap a section in a fixed card with a colored top accent."""
    content.size_hint = (1, 1)
    card = arcade.gui.UIAnchorLayout(
        width=width,
        height=height,
        size_hint=(0, 0),
        size_hint_min=(width, height),
        size_hint_max=(width, height),
    )
    card.with_background(color=(25, 34, 45, 245))
    card.with_border(width=1, color=(61, 76, 94))
    card.add(content)
    card.add(
        arcade.gui.UIWidget(width=width - 2, height=4).with_background(color=accent),
        anchor_x="center",
        anchor_y="top",
        align_y=-1,
    )
    return card


def _fixed_label(
    text: str,
    *,
    width: int,
    height: int = 36,
    font_size: int = 12,
    bold: bool = False,
    text_color=TEXT,
    anchor_x: str = "left",
) -> tuple[arcade.gui.UIAnchorLayout, arcade.gui.UILabel]:
    """Place a label in a fixed-width column so text cannot shift rows."""
    holder = arcade.gui.UIAnchorLayout(
        width=width,
        height=height,
        size_hint_min=(width, height),
        size_hint_max=(width, height),
    )
    label = arcade.gui.UILabel(
        text=text,
        height=height,
        font_size=font_size,
        bold=bold,
        text_color=text_color,
    )
    holder.add(label, anchor_x=anchor_x, anchor_y="center")
    return holder, label


def build_menu(
    manager: arcade.gui.UIManager,
    *,
    on_framework: Callable,
    on_scenario: Callable,
    on_general: Callable,
    on_info: Callable,
    on_back: Callable,
) -> None:
    content = arcade.gui.UIBoxLayout(vertical=True, space_between=11)
    content.add(_heading("MENU", "SIMULATION CONFIGURATION", 380))
    content.add(_button("Framework Settings", on_framework, 380, variant="framework"))
    content.add(_button("Scenario Settings", on_scenario, 380, variant="scenario"))
    content.add(_button("General Settings", on_general, 380, variant="general"))
    content.add(_button("Info", on_info, 380, variant="info"))
    content.add(arcade.gui.UIWidget(width=380, height=8))
    content.add(_button("Back to Simulation", on_back, 380, variant="back"))
    _add_centered(manager, content)


def build_framework_settings(
    manager: arcade.gui.UIManager,
    *,
    selected: str,
    selected_mode: str,
    utilitarian_entity_values: dict[str, float],
    kant_rules: list[tuple[str, str, bool]],
    constant_rules: list[tuple[str, str, bool]],
    constant_conflict_resolution: str,
    conflict_resolvers: list[str],
    llm_additional_instructions: str,
    llm_model: str,
    on_select: Callable[[str], None],
    on_select_mode: Callable[[str], None],
    on_save: Callable,
    on_save_llm: Callable,
    on_toggle_rule: Callable[[str, str], None],
    on_move_kant_rule: Callable[[str, int], None],
    on_constant_resolver: Callable[[str], None],
    on_back: Callable,
) -> tuple[
    dict[str, arcade.gui.UIInputText],
    arcade.gui.UIInputText | None,
    arcade.gui.UILabel,
]:
    framework_list = arcade.gui.UIBoxLayout(vertical=True, space_between=7)
    framework_list.add(_heading("FRAMEWORKS", "SELECT A FRAMEWORK", 205))
    for framework_name in FRAMEWORK_NAMES:
        prefix = "*  " if framework_name == selected else "   "
        variant = "selected" if framework_name == selected else "default"
        button = _button(
            f"{prefix}{framework_name}",
            lambda _event: None,
            205,
            variant=variant,
        )
        button.on_click = lambda _event, name=framework_name: on_select(name)
        framework_list.add(button)
    framework_list.add(arcade.gui.UIWidget(width=205, height=8))
    framework_list.add(_button("Back to Menu", on_back, 205, variant="back"))

    editor = arcade.gui.UIBoxLayout(vertical=True, space_between=9)
    inputs: dict[str, arcade.gui.UIInputText] = {}
    additional_instructions_input: arcade.gui.UIInputText | None = None
    status = arcade.gui.UILabel(text="", width=490, height=24, font_size=10)

    supports_llm = selected in {
        "Utilitarianism",
        "Kant",
        "Constant",
        "Virtue Ethics",
    }
    if supports_llm:
        mode_row = arcade.gui.UIBoxLayout(
            vertical=False,
            space_between=8,
            width=490,
            height=36,
        )
        mode_options = (
            (("llm-agent", "LLM Agent"),)
            if selected == "Virtue Ethics"
            else (("code", "Code"), ("llm-agent", "LLM Agent"))
        )
        for mode, label in mode_options:
            selected_button = mode == selected_mode
            mode_button = _button(
                f"*  {label}" if selected_button else label,
                lambda _event: None,
                150,
                variant="selected" if selected_button else "default",
                height=34,
            )
            mode_button.on_click = (
                lambda _event, implementation=mode: on_select_mode(implementation)
            )
            mode_row.add(mode_button)
        editor.add(mode_row)

    if supports_llm and selected_mode == "llm-agent":
        editor.add(
            _heading(
                f"{selected.upper()} — LLM AGENT",
                "HIDDEN BASE PROMPTS + STRUCTURED SETTINGS + YOUR INSTRUCTIONS",
                490,
            )
        )
        provider_row = arcade.gui.UIBoxLayout(
            vertical=False,
            space_between=10,
            width=490,
            height=38,
        )
        provider_holder, _provider_label = _fixed_label(
            "Provider: Google Gemini",
            width=225,
            font_size=10,
            bold=True,
        )
        model_holder, _model_label = _fixed_label(
            f"Model: {llm_model}",
            width=255,
            font_size=10,
            text_color=(96, 165, 250),
        )
        provider_row.add(provider_holder)
        provider_row.add(model_holder)
        editor.add(provider_row)
        editor.add(
            arcade.gui.UILabel(
                text=(
                    "Additional Instructions are appended after the framework's "
                    "built-in prompt. Existing values and rules are included automatically."
                ),
                width=490,
                height=48,
                font_size=10,
                text_color=MUTED,
                multiline=True,
            )
        )
        editor.add(
            arcade.gui.UILabel(
                text="ADDITIONAL INSTRUCTIONS",
                width=490,
                height=22,
                font_size=10,
                bold=True,
                text_color=TEXT,
            )
        )
        additional_instructions_input = editor.add(
            arcade.gui.UIInputText(
                text=llm_additional_instructions,
                width=490,
                height=170,
                font_size=11,
                text_color=TEXT,
                multiline=True,
            )
        )
        status.text = "Instructions are stored in the current application state."
        status.update_font(font_color=(74, 222, 128))
        editor.add(status)
        editor.add(
            _button(
                "Save Additional Instructions",
                on_save_llm,
                250,
                variant="save",
            )
        )
    elif selected == "Utilitarianism":
        editor.add(
            _heading(
                "UTILITARIANISM",
                "ASSIGN A NUMERIC VALUE OR MALUS TO EACH ENTITY MODEL",
                490,
            )
        )
        editor.add(arcade.gui.UIWidget(width=490, height=6))
        ranking_layout = arcade.gui.UIBoxLayout(
            vertical=True,
            space_between=6,
            width=400,
            size_hint_min=(400, 1),
            size_hint_max=(400, None),
        )
        rows: dict[str, arcade.gui.UIBoxLayout] = {}
        rank_labels: dict[str, arcade.gui.UILabel] = {}
        medal_dots: dict[str, RankDot] = {}

        for row_index, (entity_model, value) in enumerate(
            utilitarian_entity_values.items()
        ):
            row = arcade.gui.UIBoxLayout(
                vertical=False,
                space_between=10,
                width=400,
                height=38,
                size_hint_min=(400, 38),
                size_hint_max=(400, 38),
            ).with_background(color=(38, 48, 61, 205))
            rank_holder, rank_label = _fixed_label(
                f"{row_index + 1}.",
                width=28,
                font_size=10,
                bold=True,
                text_color=MUTED,
                anchor_x="right",
            )
            rank_labels[entity_model] = rank_label
            row.add(rank_holder)
            medal_dots[entity_model] = row.add(RankDot())
            entity_holder, _entity_label = _fixed_label(
                ENTITY_MODEL_LABELS.get(entity_model, entity_model),
                width=174,
            )
            row.add(entity_holder)
            input_widget = row.add(
                arcade.gui.UIInputText(
                    text=f"{value:g}",
                    width=120,
                    height=36,
                    size_hint_min=(120, 36),
                    size_hint_max=(120, 36),
                    font_size=12,
                    text_color=TEXT,
                )
            )
            inputs[entity_model] = input_widget
            rows[entity_model] = row
            ranking_layout.add(row)

        def reorder_ranking() -> None:
            numeric_values: dict[str, float] = {}
            for entity_model, input_widget in inputs.items():
                try:
                    value = float(input_widget.text.strip())
                    if not math.isfinite(value):
                        return
                    numeric_values[entity_model] = value
                except ValueError:
                    return

            ordered_models = _rank_entity_models(numeric_values)
            ranking_layout.clear()
            for rank, entity_model in enumerate(ordered_models, start=1):
                rank_labels[entity_model].text = f"{rank}."
                medal_index = rank - 1
                medal_dots[entity_model].set_medal_color(
                    MEDAL_COLORS[medal_index] if medal_index < 3 else None
                )
                if medal_index < 3:
                    rows[entity_model].with_background(
                        color=RANKED_ROW_COLORS[medal_index]
                    )
                else:
                    rows[entity_model].with_background(color=(38, 48, 61, 205))
                ranking_layout.add(rows[entity_model])

        for input_widget in inputs.values():
            input_widget.on_change = lambda _event: reorder_ranking()

        reorder_ranking()
        editor.add(ranking_layout)
        editor.add(status)
        editor.add(_button("Save Values", on_save, 180, variant="save"))
    elif selected in {"Kant", "Constant"}:
        is_kant = selected == "Kant"
        editor.add(
            _heading(
                selected.upper(),
                (
                    "ENABLED RULES ARE EVALUATED BY PRIORITY"
                    if is_kant
                    else "ENABLED RULES HAVE THE SAME MORAL WEIGHT"
                ),
                490,
            )
        )
        editor.add(
            arcade.gui.UILabel(
                text=(
                    "Move rules up or down to define which principle prevails."
                    if is_kant
                    else "Conflicting votes are delegated to the selected resolver."
                ),
                width=490,
                height=30,
                font_size=10,
                text_color=MUTED,
            )
        )

        rules = kant_rules if is_kant else constant_rules
        rule_list = arcade.gui.UIBoxLayout(vertical=True, space_between=6)
        for index, (rule_key, rule_label, enabled) in enumerate(rules):
            row = arcade.gui.UIBoxLayout(
                vertical=False,
                space_between=6,
                width=490,
                height=42,
                size_hint_min=(490, 42),
                size_hint_max=(490, 42),
            ).with_background(
                color=(37, 51, 62, 220) if enabled else (38, 44, 53, 190)
            )
            if is_kant:
                priority_holder, _priority_label = _fixed_label(
                    f"{index + 1}.",
                    width=28,
                    font_size=10,
                    bold=True,
                    text_color=(96, 165, 250),
                    anchor_x="right",
                )
                row.add(priority_holder)
                label_width = 274
            else:
                row.add(arcade.gui.UIWidget(width=8, height=36))
                label_width = 344

            rule_holder, _rule_label = _fixed_label(
                rule_label,
                width=label_width,
                font_size=10,
                text_color=TEXT if enabled else MUTED,
            )
            row.add(rule_holder)
            toggle_button = row.add(
                _button(
                    "ON" if enabled else "OFF",
                    lambda _event: None,
                    66,
                    variant="save" if enabled else "default",
                    height=32,
                )
            )
            toggle_button.on_click = (
                lambda _event, framework=selected, key=rule_key: on_toggle_rule(
                    framework,
                    key,
                )
            )

            if is_kant:
                up_button = row.add(
                    _button("^", lambda _event: None, 38, height=32)
                )
                down_button = row.add(
                    _button("v", lambda _event: None, 38, height=32)
                )
                up_button.disabled = index == 0
                down_button.disabled = index == len(rules) - 1
                up_button.on_click = (
                    lambda _event, key=rule_key: on_move_kant_rule(key, -1)
                )
                down_button.on_click = (
                    lambda _event, key=rule_key: on_move_kant_rule(key, 1)
                )
            rule_list.add(row)

        editor.add(rule_list)
        if not is_kant:
            resolver_row = arcade.gui.UIBoxLayout(
                vertical=False,
                space_between=10,
                width=490,
                height=38,
            )
            resolver_holder, _resolver_label = _fixed_label(
                "Conflict resolution:",
                width=178,
                font_size=11,
                bold=True,
            )
            resolver_row.add(resolver_holder)
            resolver_dropdown = resolver_row.add(
                arcade.gui.UIDropdown(
                    default=constant_conflict_resolution,
                    options=conflict_resolvers,
                    width=250,
                    height=34,
                )
            )

            def resolver_changed(event: arcade.gui.UIOnChangeEvent) -> None:
                if event.new_value is not None:
                    on_constant_resolver(str(event.new_value))

            resolver_dropdown.on_change = resolver_changed
            editor.add(arcade.gui.UIWidget(width=490, height=3))
            editor.add(resolver_row)

        status.text = "Changes are applied immediately to the simulation state."
        status.update_font(font_color=(74, 222, 128))
        editor.add(status)
    else:
        editor.add(_heading(selected.upper(), "FRAMEWORK SETTINGS", 490))
        editor.add(arcade.gui.UIWidget(width=490, height=24))
        editor.add(
            arcade.gui.UILabel(
                text="Configuration for this framework will be added in a future version.",
                width=490,
                height=60,
                font_size=12,
                text_color=MUTED,
                multiline=True,
            )
        )

    content = arcade.gui.UIBoxLayout(vertical=False, space_between=34)
    content.add(framework_list)
    content.add(editor)
    _add_centered(manager, content)
    return inputs, additional_instructions_input, status


def build_placeholder(
    manager: arcade.gui.UIManager,
    *,
    title: str,
    on_back: Callable,
) -> None:
    content = arcade.gui.UIBoxLayout(vertical=True, space_between=14)
    content.add(_heading(title.upper(), "SETTINGS", 520))
    content.add(
        arcade.gui.UILabel(
            text="This screen is reserved for a future version.",
            width=520,
            height=50,
            font_size=12,
            text_color=MUTED,
        )
    )
    content.add(_button("Back to Menu", on_back, 220, variant="back"))
    _add_centered(manager, content)


def build_report_navigation(
    manager: arcade.gui.UIManager,
    *,
    page: int,
    page_count: int,
    on_previous: Callable,
    on_next: Callable,
    on_back: Callable,
    on_restart: Callable,
) -> None:
    """Build report pagination and exit actions along the bottom edge."""
    controls = arcade.gui.UIBoxLayout(vertical=False, space_between=8)
    previous = controls.add(
        _button("Previous", on_previous, 112, height=36)
    )
    page_holder, page_label = _fixed_label(
        f"{page + 1} / {page_count}",
        width=56,
        height=36,
        font_size=9,
        bold=True,
        text_color=MUTED,
        anchor_x="center",
    )
    controls.add(page_holder)
    next_button = controls.add(_button("Next", on_next, 112, height=36))
    controls.add(arcade.gui.UIWidget(width=18, height=36))
    controls.add(_button("Back to Summary", on_back, 176, variant="back", height=36))
    controls.add(
        _button(
            "Restart Simulation",
            on_restart,
            184,
            variant="save",
            height=36,
        )
    )
    previous.disabled = page <= 0
    next_button.disabled = page >= page_count - 1
    anchor = arcade.gui.UIAnchorLayout()
    anchor.add(controls, anchor_x="center", anchor_y="bottom", align_y=12)
    manager.add(anchor)


def build_scenario_settings(
    manager: arcade.gui.UIManager,
    *,
    scenario_names: list[str],
    selected_scenario: str,
    scenario_definition: dict[str, list[dict]],
    selected_entity: tuple[str, int],
    road_y: float,
    message: str,
    on_select_scenario: Callable[[str], None],
    on_select_entity: Callable[[str, int], None],
    on_add_car: Callable,
    on_add_pedestrian: Callable,
    on_set_location: Callable,
    on_delete_entity: Callable,
    on_save: Callable,
    on_back: Callable,
) -> tuple[
    dict[str, arcade.gui.UIInputText],
    arcade.gui.UIDropdown | None,
    arcade.gui.UIDropdown | None,
    arcade.gui.UISlider | None,
    arcade.gui.UILabel,
]:
    """Build the persistent scenario and entity editor."""
    card_height = 490
    scenario_column = arcade.gui.UIBoxLayout(
        vertical=True,
        space_between=7,
        width=206,
        height=card_height,
    )
    scenario_column.add(arcade.gui.UIWidget(width=190, height=10))
    scenario_column.add(_section_heading("SCENARIOS", "SELECT A SCENARIO", 190))
    for scenario_name in scenario_names:
        selected = scenario_name == selected_scenario
        scenario_button = _button(
            f"*  {scenario_name}" if selected else scenario_name,
            lambda _event: None,
            190,
            variant="selected" if selected else "default",
            height=36,
        )
        scenario_button.on_click = (
            lambda _event, name=scenario_name: on_select_scenario(name)
        )
        scenario_column.add(scenario_button)
    scenario_column.add(
        arcade.gui.UIWidget(
            width=190,
            height=18,
            size_hint=(0, 1),
            size_hint_min=(190, 18),
        )
    )
    scenario_column.add(_button("Back to Menu", on_back, 190, variant="back"))
    scenario_column.add(arcade.gui.UIWidget(width=190, height=10))

    cars = scenario_definition["cars"]
    pedestrians = scenario_definition["pedestrians"]
    entity_column = arcade.gui.UIBoxLayout(
        vertical=True,
        space_between=6,
        width=306,
        height=card_height,
    )
    entity_column.add(arcade.gui.UIWidget(width=290, height=10))
    entity_column.add(
        _section_heading(
            "ENTITIES",
            f"{len(cars)} CAR(S)  /  {len(pedestrians)} PEDESTRIAN(S)",
            290,
        )
    )
    add_row = arcade.gui.UIBoxLayout(vertical=False, space_between=6)
    add_row.add(_button("+ Car", on_add_car, 142, variant="car", height=36))
    add_row.add(
        _button(
            "+ Pedestrian",
            on_add_pedestrian,
            142,
            variant="scenario",
            height=36,
        )
    )
    entity_column.add(add_row)

    entity_references = [
        *(("cars", index) for index in range(len(cars))),
        *(("pedestrians", index) for index in range(len(pedestrians))),
    ]
    page_size = 8
    try:
        selected_position = entity_references.index(selected_entity)
    except ValueError:
        selected_position = 0
    page_start = (selected_position // page_size) * page_size
    page_entities = entity_references[page_start : page_start + page_size]

    for entity_kind, entity_index in page_entities:
        is_selected = (entity_kind, entity_index) == selected_entity
        if entity_kind == "cars":
            text = f"CAR {entity_index + 1}"
            variant = "selected" if is_selected else "car"
        else:
            entity = pedestrians[entity_index]
            suffix = f" - {entity['label']}" if entity.get("label") else ""
            text = f"PERSON {entity_index + 1} ({entity['model']}){suffix}"
            variant = "selected" if is_selected else "scenario"
        entity_button = _button(
            f"*  {text}" if is_selected else text,
            lambda _event: None,
            290,
            variant=variant,
            height=34,
        )
        entity_button.on_click = (
            lambda _event, kind=entity_kind, index=entity_index: on_select_entity(
                kind, index
            )
        )
        entity_column.add(entity_button)

    if len(entity_references) > page_size:
        page_row = arcade.gui.UIBoxLayout(vertical=False, space_between=6)
        previous_position = max(0, page_start - page_size)
        next_position = min(
            len(entity_references) - 1,
            page_start + page_size,
        )
        previous_button = _button(
            "<",
            lambda _event: on_select_entity(*entity_references[previous_position]),
            48,
            height=30,
        )
        previous_button.disabled = page_start == 0
        page_row.add(previous_button)
        page_row.add(
            arcade.gui.UILabel(
                text=(
                    f"{page_start + 1}-"
                    f"{min(page_start + page_size, len(entity_references))} "
                    f"of {len(entity_references)}"
                ),
                width=182,
                height=30,
                font_size=9,
                text_color=MUTED,
                align="center",
            )
        )
        next_button = _button(
            ">",
            lambda _event: on_select_entity(*entity_references[next_position]),
            48,
            height=30,
        )
        next_button.disabled = page_start + page_size >= len(entity_references)
        page_row.add(next_button)
        entity_column.add(page_row)
    entity_column.add(
        arcade.gui.UIWidget(
            width=290,
            height=8,
            size_hint=(0, 1),
            size_hint_min=(290, 8),
        )
    )

    entity_kind, entity_index = selected_entity
    entity = scenario_definition[entity_kind][entity_index]
    input_widgets: dict[str, arcade.gui.UIInputText] = {}
    model_dropdown: arcade.gui.UIDropdown | None = None
    action_dropdown: arcade.gui.UIDropdown | None = None
    pedestrian_speed_slider: arcade.gui.UISlider | None = None
    editor_column = arcade.gui.UIBoxLayout(
        vertical=True,
        space_between=6,
        width=366,
        height=card_height,
    )
    editor_column.add(arcade.gui.UIWidget(width=350, height=10))
    entity_title = (
        f"CAR {entity_index + 1}"
        if entity_kind == "cars"
        else f"PEDESTRIAN {entity_index + 1}"
    )
    editor_column.add(_section_heading("ENTITY EDITOR", entity_title, 350))
    editor_column.add(
        _button(
            "Set Location",
            on_set_location,
            350,
            variant="link",
            height=36,
        )
    )
    position_row = arcade.gui.UIBoxLayout(
        vertical=False,
        space_between=10,
        width=350,
        height=30,
        size_hint_min=(350, 30),
        size_hint_max=(350, 30),
    )
    x_holder, _x_label = _fixed_label(
        f"Position X   {entity['x']:g}",
        width=170,
        height=30,
        font_size=10,
        text_color=MUTED,
    )
    x_holder.with_background(color=(31, 43, 56, 230)).with_border(
        width=1,
        color=(55, 72, 89),
    )
    y_holder, _y_label = _fixed_label(
        f"Position Y   {entity['y_offset'] + road_y:g}",
        width=170,
        height=30,
        font_size=10,
        text_color=MUTED,
    )
    y_holder.with_background(color=(31, 43, 56, 230)).with_border(
        width=1,
        color=(55, 72, 89),
    )
    position_row.add(x_holder)
    position_row.add(y_holder)
    editor_column.add(position_row)

    def add_input(label: str, key: str, value: str) -> None:
        row = arcade.gui.UIBoxLayout(
            vertical=False,
            space_between=10,
            width=350,
            height=36,
            size_hint_min=(350, 36),
            size_hint_max=(350, 36),
        )
        label_holder, _label = _fixed_label(
            label,
            width=120,
            height=36,
            font_size=10,
            text_color=MUTED,
        )
        row.add(label_holder)
        input_widgets[key] = row.add(
            arcade.gui.UIInputText(
                text=value,
                width=220,
                height=36,
                size_hint_min=(220, 36),
                size_hint_max=(220, 36),
                font_size=11,
                text_color=TEXT,
            )
        )
        editor_column.add(row)

    if entity_kind == "cars":
        add_input("Speed (km/h)", "speed_kmh", f"{entity['speed'] * 0.18:g}")
    else:
        model_row = arcade.gui.UIBoxLayout(
            vertical=False,
            space_between=10,
            width=350,
            height=36,
            size_hint_min=(350, 36),
            size_hint_max=(350, 36),
        )
        model_holder, _model_label = _fixed_label(
            "Person model",
            width=120,
            height=36,
            font_size=10,
            text_color=MUTED,
        )
        model_row.add(model_holder)
        selected_model_label = ENTITY_MODEL_LABELS.get(entity["model"], entity["model"])
        model_dropdown = model_row.add(
            arcade.gui.UIDropdown(
                default=selected_model_label,
                options=list(ENTITY_MODEL_LABELS.values()),
                width=220,
                height=36,
            )
        )
        editor_column.add(model_row)
        add_input("Small label", "label", entity.get("label") or "")
        action_row = arcade.gui.UIBoxLayout(
            vertical=False,
            space_between=10,
            width=350,
            height=36,
            size_hint_min=(350, 36),
            size_hint_max=(350, 36),
        )
        action_holder, _action_label = _fixed_label(
            "Action",
            width=120,
            height=36,
            font_size=10,
            text_color=MUTED,
        )
        action_row.add(action_holder)
        selected_action_label = PEDESTRIAN_ACTION_LABELS.get(
            entity.get("action", "still"),
            "Still",
        )
        action_dropdown = action_row.add(
            arcade.gui.UIDropdown(
                default=selected_action_label,
                options=list(PEDESTRIAN_ACTION_LABELS.values()),
                width=220,
                height=36,
            )
        )
        editor_column.add(action_row)

        speed_row = arcade.gui.UIBoxLayout(
            vertical=False,
            space_between=10,
            width=350,
            height=36,
            size_hint_min=(350, 36),
            size_hint_max=(350, 36),
        )
        speed_title_holder, _speed_title = _fixed_label(
            "Walking speed",
            width=100,
            height=36,
            font_size=10,
            text_color=MUTED,
        )
        speed_row.add(speed_title_holder)
        speed_value_holder, speed_value_label = _fixed_label(
            f"{entity.get('speed', 55.0):03.0f}",
            width=42,
            height=36,
            font_size=10,
            bold=True,
            anchor_x="right",
        )
        speed_row.add(speed_value_holder)
        pedestrian_speed_slider = speed_row.add(
            arcade.gui.UISlider(
                value=float(entity.get("speed", 55.0)),
                min_value=0.0,
                max_value=150.0,
                step=5.0,
                width=188,
                height=26,
            )
        )

        def update_speed_label(event: arcade.gui.UIOnChangeEvent) -> None:
            if event.new_value is not None:
                speed_value_label.text = f"{float(event.new_value):03.0f}"

        def update_speed_availability(event: arcade.gui.UIOnChangeEvent) -> None:
            pedestrian_speed_slider.disabled = event.new_value == "Still"

        pedestrian_speed_slider.on_change = update_speed_label
        action_dropdown.on_change = update_speed_availability
        pedestrian_speed_slider.disabled = selected_action_label == "Still"
        editor_column.add(speed_row)

    editor_column.add(
        arcade.gui.UILabel(
            text="Choose Set Location and click a point on the map.",
            width=350,
            height=20,
            font_size=8,
            text_color=MUTED,
            align="center",
        )
    )
    editor_column.add(
        arcade.gui.UIWidget(
            width=350,
            height=4,
            size_hint=(0, 1),
            size_hint_min=(350, 4),
        )
    )
    editor_column.add(
        _button(
            "Delete Entity",
            on_delete_entity,
            350,
            variant="danger",
            height=36,
        )
    )
    editor_column.add(_button("Save Scenarios", on_save, 350, variant="save", height=40))
    status = editor_column.add(
        arcade.gui.UILabel(
            text=message,
            width=350,
            height=28,
            font_size=9,
            text_color=MUTED,
            multiline=True,
            align="center",
        )
    )
    editor_column.add(arcade.gui.UIWidget(width=350, height=6))

    body = arcade.gui.UIBoxLayout(vertical=False, space_between=10)
    body.add(
        _section_card(
            scenario_column,
            width=206,
            height=card_height,
            accent=(37, 99, 235),
        )
    )
    body.add(
        _section_card(
            entity_column,
            width=306,
            height=card_height,
            accent=(13, 148, 136),
        )
    )
    body.add(
        _section_card(
            editor_column,
            width=366,
            height=card_height,
            accent=(109, 40, 217),
        )
    )
    content = arcade.gui.UIBoxLayout(vertical=True, space_between=12)
    content.add(
        _heading(
            "SCENARIO SETTINGS",
            "EDIT CARS AND PEDESTRIANS, THEN SAVE THE CATALOG",
            898,
        )
    )
    content.add(body)
    _add_centered(manager, content)
    return (
        input_widgets,
        model_dropdown,
        action_dropdown,
        pedestrian_speed_slider,
        status,
    )


def build_location_picker(
    manager: arcade.gui.UIManager,
    *,
    entity_description: str,
    on_cancel: Callable,
) -> None:
    """Build the compact overlay shown above the clickable scenario map."""
    labels = arcade.gui.UIBoxLayout(vertical=True, space_between=2)
    labels.add(
        arcade.gui.UILabel(
            text=f"SET LOCATION · {entity_description}",
            width=570,
            height=24,
            font_size=13,
            bold=True,
            text_color=TEXT,
        )
    )
    labels.add(
        arcade.gui.UILabel(
            text="Click anywhere on the map to place the entity.",
            width=570,
            height=18,
            font_size=9,
            text_color=MUTED,
        )
    )
    bar = arcade.gui.UIBoxLayout(
        vertical=False,
        space_between=18,
        width=800,
        height=58,
        size_hint_min=(800, 58),
        size_hint_max=(800, 58),
    ).with_background(color=(24, 32, 42, 245))
    bar.add(labels)
    bar.add(_button("Cancel", on_cancel, 150, variant="back", height=38))
    anchor = arcade.gui.UIAnchorLayout()
    anchor.add(bar, anchor_x="center", anchor_y="top", align_y=-10)
    manager.add(anchor)


def build_info(
    manager: arcade.gui.UIManager,
    *,
    repository_url: str,
    on_open_repository: Callable,
    on_back: Callable,
) -> None:
    content = arcade.gui.UIBoxLayout(vertical=True, space_between=14)
    content.add(_heading("ETHICAL MULTI-AGENT SIMULATION", "PROJECT INFO", 590))
    content.add(
        arcade.gui.UILabel(
            text="A 2D sandbox for exploring ethical decisions made by autonomous agents.",
            width=590,
            height=48,
            font_size=12,
            text_color=TEXT,
            multiline=True,
        )
    )
    content.add(
        arcade.gui.UILabel(
            text=repository_url,
            width=590,
            height=26,
            font_size=10,
            text_color=MUTED,
        )
    )
    content.add(
        _button("Open GitHub Repository", on_open_repository, 250, variant="link")
    )
    content.add(_button("Back to Menu", on_back, 250, variant="back"))
    _add_centered(manager, content)
