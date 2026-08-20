"""Builders for menu and settings screens.

The builders own layout only. Navigation and application state remain in the
window, which keeps the simulation independent from these widgets.
"""

from collections.abc import Callable
import math

import arcade
import arcade.gui

FRAMEWORK_NAMES = ["Utilitarianism", "Kant", "Constant", "Ross", "Virtue Ethics"]

ENTITY_MODEL_LABELS = {
    "man": "Man",
    "woman": "Woman",
    "old_man": "Old man",
    "old_woman": "Old woman",
    "boy": "Boy",
    "girl": "Girl",
    "custom": "Custom",
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
) -> arcade.gui.UIFlatButton:
    button = arcade.gui.UIFlatButton(
        text=text,
        width=width,
        height=42,
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
    utilitarian_entity_values: dict[str, float],
    on_select: Callable[[str], None],
    on_save: Callable,
    on_back: Callable,
) -> tuple[dict[str, arcade.gui.UIInputText], arcade.gui.UILabel]:
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
    status = arcade.gui.UILabel(text="", width=490, height=24, font_size=10)

    if selected == "Utilitarianism":
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
    return inputs, status


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
