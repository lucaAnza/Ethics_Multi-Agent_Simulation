"""Scenario catalog editing and map-based entity placement."""

from __future__ import annotations

from copy import deepcopy
import math

import arcade
import arcade.gui

from application.config import GITHUB_REPOSITORY
from scenarios import (
    RANDOM_SCENARIO_NAME,
    RANDOM_SETTING_VALUE,
    RandomScenarioSettings,
    save_scenario_settings,
)
from simulation import World
from simulation.config import (
    DEFAULT_CAR_START_X,
    DEFAULT_PEDESTRIAN_SPEED,
    DEFAULT_VEHICLE_SPEED_KMH,
    LANE_OFFSET,
)
from simulation.entities import PEDESTRIAN_ACTION_LABELS, PEDESTRIAN_MODEL_INFO
from ui.screens import (
    build_info,
    build_location_picker,
    build_placeholder,
    build_random_scenario_settings,
    build_scenario_settings,
)


class ScenarioEditorMixin:
    """Manage validated scenario drafts and persistence callbacks."""

    def _refresh_scenario_initial_speeds(self) -> None:
        """Build the toolbar speed lookup from the canonical scenario state."""
        self.scenario_initial_speeds = {
            name: float(definition["cars"][0]["speed"])
            for name, definition in self.scenario_definitions.items()
        }
        self.scenario_initial_speeds[RANDOM_SCENARIO_NAME] = (
            self.random_scenario_settings.initial_speed
        )

    def _open_scenario_settings(
        self,
        _event: arcade.gui.UIOnClickEvent | None = None,
        *,
        selected_scenario: str | None = None,
    ) -> None:
        self.scenario_editor_draft = deepcopy(self.scenario_definitions)
        self.random_scenario_settings_draft = self.random_scenario_settings
        requested_scenario = selected_scenario or self.current_scenario
        self.scenario_editor_scenario = (
            requested_scenario
            if requested_scenario
            in (*self.scenario_editor_draft, RANDOM_SCENARIO_NAME)
            else next(iter(self.scenario_editor_draft))
        )
        self.scenario_editor_entity = ("cars", 0)
        self.scenario_editor_message = ""
        self._show_scenario_editor()

    def _show_scenario_editor(self) -> None:
        self.active_screen = "scenario_settings"
        self.manager.clear()
        scenario_names = [*self.scenario_editor_draft, RANDOM_SCENARIO_NAME]
        if self.scenario_editor_scenario == RANDOM_SCENARIO_NAME:
            (
                self.random_scenario_inputs,
                self.random_scenario_dropdowns,
                self.scenario_editor_status,
            ) = build_random_scenario_settings(
                self.manager,
                scenario_names=scenario_names,
                selected_scenario=self.scenario_editor_scenario,
                settings=self.random_scenario_settings_draft,
                message=self.scenario_editor_message,
                on_select_scenario=self._select_scenario_to_edit,
                on_save=self._save_scenario_settings,
                on_back=self._open_menu,
            )
            return
        definition = self.scenario_editor_draft[self.scenario_editor_scenario]
        entity_kind, entity_index = self.scenario_editor_entity
        if (
            entity_kind not in {"cars", "pedestrians"}
            or entity_index >= len(definition[entity_kind])
        ):
            self.scenario_editor_entity = ("cars", 0)
        (
            self.scenario_editor_inputs,
            self.scenario_editor_model,
            self.scenario_editor_action,
            self.scenario_editor_pedestrian_speed,
            self.scenario_editor_status,
        ) = build_scenario_settings(
            self.manager,
            scenario_names=scenario_names,
            selected_scenario=self.scenario_editor_scenario,
            scenario_definition=definition,
            selected_entity=self.scenario_editor_entity,
            road_y=self.world.road_y,
            message=self.scenario_editor_message,
            on_select_scenario=self._select_scenario_to_edit,
            on_select_entity=self._select_scenario_entity,
            on_add_car=self._add_scenario_car,
            on_add_pedestrian=self._add_scenario_pedestrian,
            on_set_location=self._open_scenario_location_picker,
            on_delete_entity=self._delete_scenario_entity,
            on_save=self._save_scenario_settings,
            on_back=self._open_menu,
        )

    def _set_scenario_editor_error(self, message: str) -> None:
        self.scenario_editor_message = message
        if self.scenario_editor_status is not None:
            self.scenario_editor_status.text = message
            self.scenario_editor_status.update_font(font_color=(248, 113, 113))

    def _commit_scenario_editor_form(self) -> bool:
        """Copy the visible fixed or random form into its in-memory draft."""
        if self.scenario_editor_scenario == RANDOM_SCENARIO_NAME:
            return self._commit_random_scenario_form()

        entity_kind, entity_index = self.scenario_editor_entity
        entity = self.scenario_editor_draft[self.scenario_editor_scenario][entity_kind][
            entity_index
        ]
        original_entity = dict(entity)

        def number(
            key: str,
            label: str,
            *,
            minimum: float | None = None,
        ) -> float | None:
            widget = self.scenario_editor_inputs[key]
            try:
                value = float(widget.text.strip())
                if not math.isfinite(value) or (
                    minimum is not None and value < minimum
                ):
                    raise ValueError
            except ValueError:
                widget.invalid = True
                self._set_scenario_editor_error(f"Enter a valid value for {label}.")
                return None
            widget.invalid = False
            return value

        if entity_kind == "cars":
            speed_kmh = number("speed_kmh", "Speed", minimum=0.0)
            if speed_kmh is None:
                return False
            entity.update({"speed": speed_kmh})
        else:
            selected_label = (
                self.scenario_editor_model.value
                if self.scenario_editor_model is not None
                else "Man"
            )
            model = next(
                (
                    key
                    for key, info in PEDESTRIAN_MODEL_INFO.items()
                    if info["label"] == selected_label
                ),
                "man",
            )
            label = self.scenario_editor_inputs["label"].text.strip()
            selected_action_label = (
                self.scenario_editor_action.value
                if self.scenario_editor_action is not None
                else "Still"
            )
            action = next(
                (
                    key
                    for key, display_name in PEDESTRIAN_ACTION_LABELS.items()
                    if display_name == selected_action_label
                ),
                "still",
            )
            pedestrian_speed = (
                float(self.scenario_editor_pedestrian_speed.value)
                if self.scenario_editor_pedestrian_speed is not None
                else DEFAULT_PEDESTRIAN_SPEED
            )
            entity.update(
                {
                    "model": model,
                    "label": label or None,
                    "action": action,
                    "speed": pedestrian_speed,
                }
            )
        if entity != original_entity:
            self.scenario_editor_message = "Unsaved changes."
        return True

    def _commit_random_scenario_form(self) -> bool:
        values: dict[str, object] = {}
        for key, widget in self.random_scenario_inputs.items():
            try:
                values[key] = float(widget.text.strip())
            except ValueError:
                widget.invalid = True
                self._set_scenario_editor_error(
                    f"Enter a valid numeric value for {key.replace('_', ' ')}."
                )
                return False
            widget.invalid = False

        if self.random_scenario_dropdowns["vision_mode"].value == "Random":
            values["vision_distance"] = RANDOM_SETTING_VALUE
        if self.random_scenario_dropdowns["max_shifts_mode"].value == "Random":
            values["max_shifts"] = RANDOM_SETTING_VALUE
        try:
            updated = RandomScenarioSettings.from_mapping(values)
        except ValueError as error:
            self._set_scenario_editor_error(str(error))
            return False
        if updated != self.random_scenario_settings_draft:
            self.random_scenario_settings_draft = updated
            self.scenario_editor_message = "Unsaved random generator changes."
        return True

    def _select_scenario_to_edit(self, scenario_name: str) -> None:
        if not self._commit_scenario_editor_form():
            return
        self.scenario_editor_scenario = scenario_name
        self.scenario_editor_entity = ("cars", 0)
        self._show_scenario_editor()

    def _select_scenario_entity(self, entity_kind: str, entity_index: int) -> None:
        if not self._commit_scenario_editor_form():
            return
        self.scenario_editor_entity = (entity_kind, entity_index)
        self._show_scenario_editor()

    def _add_scenario_car(
        self, _event: arcade.gui.UIOnClickEvent | None = None
    ) -> None:
        if not self._commit_scenario_editor_form():
            return
        cars = self.scenario_editor_draft[self.scenario_editor_scenario]["cars"]
        cars.append(
            {
                "x": DEFAULT_CAR_START_X + 110.0 * len(cars),
                "y_offset": -LANE_OFFSET,
                "speed": DEFAULT_VEHICLE_SPEED_KMH,
            }
        )
        self.scenario_editor_entity = ("cars", len(cars) - 1)
        self.scenario_editor_message = "Car added. Save to make it persistent."
        self._show_scenario_editor()

    def _add_scenario_pedestrian(
        self, _event: arcade.gui.UIOnClickEvent | None = None
    ) -> None:
        if not self._commit_scenario_editor_form():
            return
        pedestrians = self.scenario_editor_draft[self.scenario_editor_scenario][
            "pedestrians"
        ]
        pedestrians.append(
            {
                "x": self.width / 2,
                "y_offset": self.height / 2 - self.world.road_y,
                "model": "man",
                "label": None,
                "action": "still",
                "speed": DEFAULT_PEDESTRIAN_SPEED,
            }
        )
        self.scenario_editor_entity = ("pedestrians", len(pedestrians) - 1)
        self.scenario_editor_message = "Pedestrian added. Save to make it persistent."
        self._show_scenario_editor()

    def _open_scenario_location_picker(
        self, _event: arcade.gui.UIOnClickEvent | None = None
    ) -> None:
        if not self._commit_scenario_editor_form():
            return
        entity_kind, entity_index = self.scenario_editor_entity
        entity_name = (
            f"Car {entity_index + 1}"
            if entity_kind == "cars"
            else f"Pedestrian {entity_index + 1}"
        )
        self.active_screen = "scenario_location_picker"
        self.scenario_location_preview = World(
            self.width,
            self.height,
            self.scenario_editor_scenario,
            self.scenario_editor_draft,
        )
        entity = self.scenario_editor_draft[self.scenario_editor_scenario][entity_kind][
            entity_index
        ]
        self.scenario_location_cursor = (
            float(entity["x"]),
            self.world.road_y + float(entity["y_offset"]),
        )
        self.manager.clear()
        build_location_picker(
            self.manager,
            entity_description=entity_name,
            on_cancel=self._cancel_scenario_location_picker,
        )

    def _cancel_scenario_location_picker(
        self, _event: arcade.gui.UIOnClickEvent | None = None
    ) -> None:
        self.scenario_location_preview = None
        self._show_scenario_editor()

    def _delete_scenario_entity(
        self, _event: arcade.gui.UIOnClickEvent | None = None
    ) -> None:
        entity_kind, entity_index = self.scenario_editor_entity
        entities = self.scenario_editor_draft[self.scenario_editor_scenario][
            entity_kind
        ]
        if entity_kind == "cars" and len(entities) == 1:
            self._set_scenario_editor_error("A scenario must contain at least one car.")
            return
        entities.pop(entity_index)
        if entities:
            self.scenario_editor_entity = (
                entity_kind,
                min(entity_index, len(entities) - 1),
            )
        else:
            self.scenario_editor_entity = ("cars", 0)
        self.scenario_editor_message = "Entity removed. Save to make it persistent."
        self._show_scenario_editor()

    def _save_scenario_settings(
        self, _event: arcade.gui.UIOnClickEvent | None = None
    ) -> None:
        if not self._commit_scenario_editor_form():
            return
        try:
            saved_settings = save_scenario_settings(
                self.scenario_editor_draft,
                self.random_scenario_settings_draft,
            )
        except (OSError, ValueError) as error:
            self._set_scenario_editor_error(f"Could not save scenarios: {error}")
            return

        self.scenario_definitions = saved_settings.definitions
        self.random_scenario_settings = saved_settings.random_scenario
        self.scenario_editor_draft = deepcopy(saved_settings.definitions)
        self.random_scenario_settings_draft = saved_settings.random_scenario
        self.scenario_names = [*saved_settings.definitions, RANDOM_SCENARIO_NAME]
        self._refresh_scenario_initial_speeds()
        self.world.set_scenario_definitions(saved_settings.definitions)
        self.world.set_random_scenario_settings(self.random_scenario_settings)
        self.world.reset(self.current_scenario)
        self._apply_current_scenario_vehicle_settings()
        self._sync_vehicle_control_values()
        self._reset_run_state()
        self.scenario_editor_message = "Scenarios saved and applied to the simulation."
        if self.scenario_editor_status is not None:
            self.scenario_editor_status.text = self.scenario_editor_message
            self.scenario_editor_status.update_font(font_color=(74, 222, 128))

    def _open_general_settings(
        self, _event: arcade.gui.UIOnClickEvent | None = None
    ) -> None:
        self.active_screen = "general_settings"
        self.manager.clear()
        build_placeholder(
            self.manager,
            title="General Settings",
            on_back=self._open_menu,
        )

    def _open_info(self, _event: arcade.gui.UIOnClickEvent | None = None) -> None:
        self.active_screen = "info"
        self.manager.clear()
        build_info(
            self.manager,
            repository_url=GITHUB_REPOSITORY,
            on_open_repository=self._open_repository,
            on_back=self._open_menu,
        )
