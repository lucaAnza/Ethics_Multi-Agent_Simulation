"""Colors and reusable widget styles shared by the Arcade interface."""

import arcade.gui

TEXT = (238, 243, 248)
MUTED = (155, 170, 185)
PANEL = (25, 34, 45, 245)
BORDER = (61, 76, 94)
FRAMEWORK_SELECTION = (56, 189, 248)
SCENARIO_SELECTION = (102, 0, 255)
MODE_SELECTION = (153, 204, 0)

_DROPDOWN_BACKGROUND = (43, 12, 74)
_DROPDOWN_HOVER = (51, 65, 85)
_DROPDOWN_PRESS = (30, 41, 59)


def dropdown_styles(
    selected_color=TEXT,
) -> dict[str, dict[str, arcade.gui.UIFlatButton.UIStyle]]:
    """Return a complete dropdown palette without Arcade's green default."""
    style = arcade.gui.UIFlatButton.UIStyle

    def button_states(font_color) -> dict[str, arcade.gui.UIFlatButton.UIStyle]:
        return {
            "normal": style(
                bg=_DROPDOWN_BACKGROUND,
                font_color=font_color,
                border=BORDER,
                border_width=1,
            ),
            "hover": style(
                bg=_DROPDOWN_HOVER,
                font_color=font_color,
                border=(100, 116, 139),
                border_width=1,
            ),
            "press": style(
                bg=_DROPDOWN_PRESS,
                font_color=font_color,
                border=(148, 163, 184),
                border_width=1,
            ),
            "disabled": style(
                bg=(55, 65, 78),
                font_color=MUTED,
                border=BORDER,
                border_width=1,
            ),
        }

    return {
        "primary_style": button_states(selected_color),
        "dropdown_style": button_states(TEXT),
        "active_style": button_states(selected_color),
    }
