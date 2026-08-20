"""Builders for menu and settings screens.

The builders own layout only. Navigation and application state remain in the
window, which keeps the simulation independent from these widgets.
"""

from collections.abc import Callable

import arcade.gui

FRAMEWORK_NAMES = ["Utilitarianism", "Kant", "Constant", "Ross", "Virtue Ethics"]

TEXT = (238, 243, 248)
MUTED = (155, 170, 185)

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
    utilitarian_values: dict[str, float],
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
                "ASSIGN A NUMERIC VALUE OR MALUS TO EACH PERSON TYPE",
                490,
            )
        )
        editor.add(arcade.gui.UIWidget(width=490, height=6))
        for person_type, value in utilitarian_values.items():
            row = arcade.gui.UIBoxLayout(vertical=False, space_between=16)
            row.add(
                arcade.gui.UILabel(
                    text=person_type,
                    width=250,
                    height=36,
                    font_size=12,
                    text_color=TEXT,
                )
            )
            input_widget = row.add(
                arcade.gui.UIInputText(
                    text=f"{value:g}",
                    width=120,
                    height=36,
                    font_size=12,
                    text_color=TEXT,
                )
            )
            inputs[person_type] = input_widget
            editor.add(row)
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
