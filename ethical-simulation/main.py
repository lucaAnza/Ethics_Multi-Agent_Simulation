"""Interactive entry point for Ethical Multi-Agent Simulation."""

from copy import deepcopy
import math
import webbrowser

import arcade
import arcade.gui

from decision_engine import (
    DRIVING,
    EXECUTING_DECISION,
    WAITING_FOR_LLM,
    CodeDecisionEngine,
    LLMDecisionEngine,
)
from ethics.base import (
    CHANGE_LANE,
    STAY,
    DecisionContext as EthicalDecisionContext,
    EthicalDecision,
)
from ethics.utilitarian import DEFAULT_ENTITIES_VALUES
from ethics.constant import (
    CONFLICT_RESOLVERS,
    UTILITARIAN_EVALUATION,
    ConstantFramework,
)
from ethics.kant import KantFramework
from ethics.rules import DEFAULT_RULE_ENABLED, DEFAULT_RULE_ORDER, MORAL_RULES
from ethics.utilitarian import UtilitarianFramework
from ethics.virtue import VirtueEthicsFramework
from llm import GeminiClient, PromptBuilder
from llm.errors import safe_error_message
from scenarios import load_scenario_definitions, save_scenario_definitions
from simulation import DetectedIncident, World
from simulation.entities import Pedestrian
from ui.report import SimulationReportData, SimulationReportRenderer
from ui.screens import (
    ENTITY_MODEL_LABELS,
    PEDESTRIAN_ACTION_LABELS,
    build_framework_settings,
    build_info,
    build_location_picker,
    build_menu,
    build_placeholder,
    build_report_navigation,
    build_scenario_settings,
)

SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
TOOLBAR_HEIGHT = 72

CODE_MODE = "code"
LLM_MODE = "llm-agent"
FRAMEWORK_IMPLEMENTATIONS = {
    "Utilitarianism": (CODE_MODE, LLM_MODE),
    "Kant": (CODE_MODE, LLM_MODE),
    "Constant": (CODE_MODE, LLM_MODE),
    "Virtue Ethics": (LLM_MODE,),
}
FRAMEWORKS = list(FRAMEWORK_IMPLEMENTATIONS)
LLM_FRAMEWORKS = {
    framework_name
    for framework_name, implementations in FRAMEWORK_IMPLEMENTATIONS.items()
    if LLM_MODE in implementations
}
FRAMEWORK_OPTIONS = [
    f"{framework_name} ({implementation})"
    for framework_name, implementations in FRAMEWORK_IMPLEMENTATIONS.items()
    for implementation in implementations
]
GITHUB_REPOSITORY = "https://github.com/lucaAnza/Ethics_Multi-Agent_Simulation"

REPORT_BUTTON_STYLE = {
    "normal": arcade.gui.UIFlatButton.UIStyle(
        bg=(251, 146, 60),
        font_color=(31, 41, 55),
    ),
    "hover": arcade.gui.UIFlatButton.UIStyle(
        bg=(253, 186, 116),
        font_color=(31, 41, 55),
        border=(255, 237, 213),
        border_width=1,
    ),
    "press": arcade.gui.UIFlatButton.UIStyle(
        bg=(234, 88, 12),
        font_color=(255, 247, 237),
    ),
    "disabled": arcade.gui.UIFlatButton.UIStyle(
        bg=(120, 85, 58),
        font_color=(203, 213, 225),
    ),
}


class SimulationWindow(arcade.Window):
    def __init__(self) -> None:
        super().__init__(
            SCREEN_WIDTH,
            SCREEN_HEIGHT,
            "Ethical Multi-Agent Simulation",
            resizable=True,
        )
        self.set_minimum_size(1150, 500)
        self.current_framework = "Utilitarianism"
        self.current_implementation = CODE_MODE
        self.framework_editor_mode = CODE_MODE
        self.scenario_definitions = load_scenario_definitions()
        self.scenario_names = list(self.scenario_definitions)
        self.current_scenario = (
            "Scenario 1"
            if "Scenario 1" in self.scenario_definitions
            else self.scenario_names[0]
        )
        self.active_screen = "simulation"
        self.is_running = False
        self.time_scale = 1.0
        self.vision_distance = 300.0
        self.decision_distance = 120.0
        self.max_spostamenti = 2
        self.simulation_finished = False
        self.last_decision: EthicalDecision | None = None
        self.decision_phase = DRIVING
        self.decision_sequence = 0
        self.pending_world_context: DetectedIncident | None = None

        self.world = World(
            self.width,
            self.height,
            self.current_scenario,
            self.scenario_definitions,
        )
        self.world.configure_vehicle(
            vision_distance=self.vision_distance,
            decision_distance=self.decision_distance,
            max_spostamenti=self.max_spostamenti,
        )
        self.framework_settings = {
            "Utilitarianism": dict(DEFAULT_ENTITIES_VALUES),
            "Kant": {
                "rule_order": list(DEFAULT_RULE_ORDER),
                "enabled_rules": dict(DEFAULT_RULE_ENABLED),
            },
            "Constant": {
                "enabled_rules": dict(DEFAULT_RULE_ENABLED),
                "conflict_resolution": UTILITARIAN_EVALUATION,
            },
        }
        self.ethical_frameworks = {
            "Utilitarianism": UtilitarianFramework(
                self.framework_settings["Utilitarianism"]
            ),
            "Kant": KantFramework(
                rule_order=self.framework_settings["Kant"]["rule_order"],
                enabled_rules=self.framework_settings["Kant"]["enabled_rules"],
            ),
            "Constant": ConstantFramework(
                enabled_rules=self.framework_settings["Constant"]["enabled_rules"],
                conflict_resolution=self.framework_settings["Constant"][
                    "conflict_resolution"
                ],
                entity_values=self.framework_settings["Utilitarianism"],
            ),
            "Virtue Ethics": VirtueEthicsFramework(),
        }
        self.llm_additional_instructions = {
            framework_name: "" for framework_name in sorted(LLM_FRAMEWORKS)
        }
        self.code_decision_engine = CodeDecisionEngine()
        self.llm_decision_engine = LLMDecisionEngine(
            client=GeminiClient(),
            prompt_builder=PromptBuilder(),
        )
        self.utilitarian_entity_inputs: dict[str, arcade.gui.UIInputText] = {}
        self.llm_additional_instructions_input: arcade.gui.UIInputText | None = None
        self.framework_status_label: arcade.gui.UILabel | None = None
        self.scenario_initial_speeds = {
            name: float(definition["cars"][0]["speed"])
            for name, definition in self.scenario_definitions.items()
        }
        self.scenario_editor_draft = deepcopy(self.scenario_definitions)
        self.scenario_editor_scenario = self.current_scenario
        self.scenario_editor_entity = ("cars", 0)
        self.scenario_editor_inputs: dict[str, arcade.gui.UIInputText] = {}
        self.scenario_editor_model: arcade.gui.UIDropdown | None = None
        self.scenario_editor_action: arcade.gui.UIDropdown | None = None
        self.scenario_editor_pedestrian_speed: arcade.gui.UISlider | None = None
        self.scenario_editor_status: arcade.gui.UILabel | None = None
        self.scenario_editor_message = ""
        self.scenario_location_preview: World | None = None
        self.scenario_location_cursor = (self.width / 2, self.height / 2)
        self.scenario_location_text = arcade.Text(
            "You are moving this entity",
            0,
            0,
            (190, 145, 25),
            11,
            anchor_x="center",
            anchor_y="bottom",
            bold=True,
        )
        self._hud_texts = self._create_hud_texts()
        self._perception_texts = self._create_perception_texts()
        self._end_texts = self._create_end_texts()
        self._llm_loading_texts = self._create_llm_loading_texts()
        self.report_renderer = SimulationReportRenderer()
        self.report_page = 0
        self.manager = arcade.gui.UIManager()
        self._setup_toolbar()
        self.manager.enable()
        arcade.set_background_color((91, 145, 79))

    def _setup_toolbar(self) -> None:
        def section(title: str, controls: arcade.gui.UIBoxLayout, width: int):
            layout = arcade.gui.UIBoxLayout(vertical=True, space_between=3)
            layout.add(
                arcade.gui.UILabel(
                    text=title,
                    width=width,
                    height=13,
                    font_size=8,
                    text_color=(155, 170, 185),
                )
            )
            layout.add(controls)
            return layout

        def separator():
            return arcade.gui.UIWidget(width=1, height=50).with_background(
                color=(78, 91, 105)
            )

        def fixed_label(text: str, width: int, font_size: int = 10):
            """Keep changing text from resizing the surrounding toolbar layout."""
            holder = arcade.gui.UIAnchorLayout(
                width=width,
                height=34,
                size_hint_min=(width, 34),
                size_hint_max=(width, 34),
            )
            label = arcade.gui.UILabel(text=text, height=34, font_size=font_size)
            holder.add(label, anchor_x="left", anchor_y="center")
            return holder, label

        row = arcade.gui.UIBoxLayout(vertical=False, space_between=10)

        selection_controls = arcade.gui.UIBoxLayout(vertical=False, space_between=5)
        framework = selection_controls.add(
            arcade.gui.UIDropdown(
                default=self._framework_option(
                    self.current_framework,
                    self.current_implementation,
                ),
                options=FRAMEWORK_OPTIONS,
                width=185,
                height=34,
            )
        )
        scenario = selection_controls.add(
            arcade.gui.UIDropdown(
                default=self.current_scenario,
                options=self.scenario_names,
                width=105,
                height=34,
            )
        )
        row.add(section("FRAMEWORK / SIMULATION", selection_controls, 295))
        row.add(separator())

        playback_controls = arcade.gui.UIBoxLayout(vertical=False, space_between=5)
        time_holder, self.time_scale_label = fixed_label(
            f"Time x{self.time_scale:.2f}", 62
        )
        playback_controls.add(time_holder)
        time_slider = playback_controls.add(
            arcade.gui.UISlider(
                value=self.time_scale,
                min_value=0.25,
                max_value=2.0,
                step=0.25,
                width=75,
                height=26,
            )
        )
        for label, handler, width in (
            (">", self._play, 34),
            ("||", self._pause, 34),
            ("[]", self._stop, 34),
        ):
            button = playback_controls.add(
                arcade.gui.UIFlatButton(text=label, width=width, height=34)
            )
            button.on_click = handler
        row.add(section("TIME / CONTROLS", playback_controls, 239))
        row.add(separator())

        vehicle_controls = arcade.gui.UIBoxLayout(vertical=False, space_between=4)
        initial_kmh = self.scenario_initial_speeds[self.current_scenario] * 0.18
        initial_holder, self.initial_speed_label = fixed_label(
            f"Speed {initial_kmh:02.0f}", 52, font_size=8
        )
        vehicle_controls.add(initial_holder)
        self.initial_speed_slider = vehicle_controls.add(
            arcade.gui.UISlider(
                value=initial_kmh,
                min_value=5,
                max_value=50,
                step=1,
                width=48,
                height=26,
            )
        )
        vision_holder, self.vision_distance_label = fixed_label(
            f"Vision {self.vision_distance:.0f}",
            62,
            font_size=8,
        )
        vehicle_controls.add(vision_holder)
        self.vision_distance_slider = vehicle_controls.add(
            arcade.gui.UISlider(
                value=self.vision_distance,
                min_value=150,
                max_value=500,
                step=10,
                width=50,
                height=26,
            )
        )
        decision_holder, self.decision_distance_label = fixed_label(
            f"Decision {self.decision_distance:.0f}",
            72,
            font_size=8,
        )
        vehicle_controls.add(decision_holder)
        self.decision_distance_slider = vehicle_controls.add(
            arcade.gui.UISlider(
                value=self.decision_distance,
                min_value=30,
                max_value=250,
                step=10,
                width=50,
                height=26,
            )
        )
        shifts_holder, self.max_spostamenti_label = fixed_label(
            f"Max shifts {self.max_spostamenti}",
            60,
            font_size=8,
        )
        vehicle_controls.add(shifts_holder)
        self.max_spostamenti_slider = vehicle_controls.add(
            arcade.gui.UISlider(
                value=self.max_spostamenti,
                min_value=0,
                max_value=5,
                step=1,
                width=42,
                height=26,
            )
        )
        row.add(section("VEHICLE VARIABLES", vehicle_controls, 448))
        row.add(separator())

        app_controls = arcade.gui.UIBoxLayout(vertical=False, space_between=5)
        menu_button = app_controls.add(
            arcade.gui.UIFlatButton(text="Menu", width=82, height=34)
        )
        menu_button.on_click = self._open_menu
        row.add(section("APPLICATION", app_controls, 82))

        framework.on_change = self._framework_changed
        scenario.on_change = self._scenario_changed
        time_slider.on_change = self._time_scale_changed
        self.initial_speed_slider.on_change = self._initial_speed_changed
        self.vision_distance_slider.on_change = self._vision_distance_changed
        self.decision_distance_slider.on_change = self._decision_distance_changed
        self.max_spostamenti_slider.on_change = self._max_spostamenti_changed
        anchor = arcade.gui.UIAnchorLayout()
        anchor.add(row, anchor_x="center", anchor_y="top", align_y=-8)
        self.manager.add(anchor)

    def _framework_changed(self, event: arcade.gui.UIOnChangeEvent) -> None:
        if event.new_value is not None:
            framework_name, implementation = self._parse_framework_option(
                str(event.new_value)
            )
            self._cancel_pending_decision()
            self.current_framework = framework_name
            self.current_implementation = implementation
            self.last_decision = None

    @staticmethod
    def _framework_option(framework_name: str, implementation: str) -> str:
        return f"{framework_name} ({implementation})"

    @staticmethod
    def _parse_framework_option(option: str) -> tuple[str, str]:
        for implementation in (LLM_MODE, CODE_MODE):
            suffix = f" ({implementation})"
            if option.endswith(suffix):
                framework_name = option[: -len(suffix)]
                if framework_name in FRAMEWORKS:
                    allowed = FRAMEWORK_IMPLEMENTATIONS[framework_name]
                    if implementation in allowed:
                        return framework_name, implementation
                    return framework_name, allowed[0]
        return "Utilitarianism", CODE_MODE

    def _reset_framework_state(self) -> None:
        for framework in self.ethical_frameworks.values():
            framework.reset()

    def _reset_run_state(self) -> None:
        self._cancel_pending_decision()
        self.is_running = False
        self.simulation_finished = False
        self.last_decision = None
        self.decision_sequence = 0
        self.decision_phase = DRIVING
        self._reset_framework_state()

    def _scenario_changed(self, event: arcade.gui.UIOnChangeEvent) -> None:
        if event.new_value is not None:
            self.current_scenario = event.new_value
            self.world.reset(self.current_scenario)
            self.world.configure_vehicle(
                vision_distance=self.vision_distance,
                decision_distance=self.decision_distance,
                max_spostamenti=self.max_spostamenti,
            )
            speed = self.scenario_initial_speeds[self.current_scenario]
            self.world.cars[0].speed = speed
            self.initial_speed_slider.value = speed * 0.18
            self.initial_speed_label.text = f"Speed {speed * 0.18:02.0f}"
            self._reset_run_state()

    def _time_scale_changed(self, event: arcade.gui.UIOnChangeEvent) -> None:
        if event.new_value is not None:
            self.time_scale = float(event.new_value)
            self.time_scale_label.text = f"Time x{self.time_scale:.2f}"

    def _initial_speed_changed(self, event: arcade.gui.UIOnChangeEvent) -> None:
        if event.new_value is not None:
            speed_kmh = float(event.new_value)
            speed = speed_kmh / 0.18
            self.scenario_initial_speeds[self.current_scenario] = speed
            self.world.cars[0].speed = speed
            self.initial_speed_label.text = f"Speed {speed_kmh:02.0f}"

    def _vision_distance_changed(self, event: arcade.gui.UIOnChangeEvent) -> None:
        if event.new_value is not None:
            self.vision_distance = float(event.new_value)
            if self.decision_distance > self.vision_distance:
                self.decision_distance = self.vision_distance
                self.decision_distance_slider.value = self.decision_distance
                self.decision_distance_label.text = (
                    f"Decision {self.decision_distance:.0f}"
                )
            self.vision_distance_label.text = f"Vision {self.vision_distance:.0f}"
            self.world.configure_vehicle(
                vision_distance=self.vision_distance,
                decision_distance=self.decision_distance,
            )

    def _decision_distance_changed(self, event: arcade.gui.UIOnChangeEvent) -> None:
        if event.new_value is not None:
            requested_distance = float(event.new_value)
            self.decision_distance = min(requested_distance, self.vision_distance)
            if requested_distance != self.decision_distance:
                self.decision_distance_slider.value = self.decision_distance
            self.decision_distance_label.text = (
                f"Decision {self.decision_distance:.0f}"
            )
            self.world.configure_vehicle(
                decision_distance=self.decision_distance,
            )

    def _max_spostamenti_changed(self, event: arcade.gui.UIOnChangeEvent) -> None:
        if event.new_value is not None:
            requested_max = int(round(float(event.new_value)))
            self.world.configure_vehicle(max_spostamenti=requested_max)
            self.max_spostamenti = self.world.max_spostamenti
            if requested_max != self.max_spostamenti:
                self.max_spostamenti_slider.value = self.max_spostamenti
            self.max_spostamenti_label.text = f"Max shifts {self.max_spostamenti}"

    def _play(self, _event: arcade.gui.UIOnClickEvent) -> None:
        if self.simulation_finished:
            return
        self.is_running = True

    def _pause(self, _event: arcade.gui.UIOnClickEvent) -> None:
        self.is_running = False

    def _maybe_trigger_ethical_decision(self) -> None:
        world_context = self.world.next_decision_context()
        if world_context is None:
            return
        car = self.world.primary_car
        context = EthicalDecisionContext.from_state(
            decision_id=self.decision_sequence + 1,
            vehicle_position=car.x if car is not None else 0.0,
            state=world_context.state,
            lane_changes_remaining=self.world.lane_changes_remaining,
        )
        framework = self.ethical_frameworks.get(self.current_framework)
        if self.current_implementation == LLM_MODE:
            try:
                started = self.llm_decision_engine.submit(
                    framework_name=self.current_framework,
                    framework_settings=self._llm_framework_settings(
                        self.current_framework
                    ),
                    additional_instructions=self.llm_additional_instructions.get(
                        self.current_framework,
                        "",
                    ),
                    context=context,
                )
            except Exception as error:
                error_message = safe_error_message(error)
                decision = EthicalDecision(
                    STAY,
                    (
                        f"LLM Agent could not start: {error_message}. "
                        "Safe fallback selected STAY."
                    ),
                    {
                        "mode": LLM_MODE,
                        "model": self.llm_decision_engine.model_name,
                        "latency_ms": 0,
                        "fallback": True,
                        "attempts": 0,
                        "llm_error": error_message,
                    },
                )
                self._apply_ethical_decision(
                    world_context,
                    self.current_framework,
                    context,
                    decision,
                )
                return
            if started:
                self.pending_world_context = world_context
                self.decision_phase = WAITING_FOR_LLM
            return

        if framework is None:
            decision = EthicalDecision(
                STAY,
                "No active framework; keeping the current lane",
                {"mode": CODE_MODE},
            )
        else:
            decision = self.code_decision_engine.decide(framework, context)
        self._apply_ethical_decision(
            world_context,
            self.current_framework,
            context,
            decision,
        )

    def _llm_framework_settings(self, framework_name: str) -> dict:
        """Return only the selected framework's structured configuration."""
        if framework_name == "Utilitarianism":
            return {
                "entity_values": deepcopy(
                    self.framework_settings["Utilitarianism"]
                )
            }
        settings = deepcopy(self.framework_settings.get(framework_name, {}))
        if framework_name == "Constant":
            settings["entity_values"] = deepcopy(
                self.framework_settings["Utilitarianism"]
            )
        return settings

    def _poll_llm_decision(self) -> None:
        result = self.llm_decision_engine.poll()
        if result is None:
            return
        world_context = self.pending_world_context
        self.pending_world_context = None
        if world_context is None:
            self.decision_phase = DRIVING
            return
        self._apply_ethical_decision(
            world_context,
            result.framework_name,
            result.context,
            result.decision,
        )

    def _apply_ethical_decision(
        self,
        world_context: DetectedIncident,
        framework_name: str,
        context: EthicalDecisionContext,
        decision: EthicalDecision,
    ) -> None:
        if decision.action not in {STAY, CHANGE_LANE}:
            decision = EthicalDecision(
                STAY,
                "Invalid decision action; safe fallback selected STAY.",
                {**decision.details, "fallback": True},
            )

        actual_decision = decision
        lane_change_started = False
        if decision.action == CHANGE_LANE:
            lane_change_started = self.world.request_lane_change()
            if not lane_change_started:
                actual_decision = EthicalDecision(
                    STAY,
                    decision.reason,
                    {
                        **decision.details,
                        "recommended_action": decision.action,
                        "lane_change_blocked": True,
                    },
                )

        self.world.mark_decision_handled(world_context)
        self.decision_sequence = context.decision_id
        framework = self.ethical_frameworks.get(framework_name)
        if framework is not None:
            framework.record_decision(
                actual_decision,
                context=context,
            )
        self.last_decision = actual_decision
        self.decision_phase = (
            EXECUTING_DECISION if lane_change_started else DRIVING
        )

        print(f"\n[ETHICAL DECISION] Framework: {framework_name}")
        print(f"  Implementation: {actual_decision.details.get('mode', CODE_MODE)}")
        print(
            "  Current lane entities: "
            f"{len(context.current_lane_entities)}"
        )
        print(
            "  Other lane entities: "
            f"{len(context.other_lane_entities)}"
        )
        print(f"  Framework action: {decision.action}")
        print(f"  Applied action: {actual_decision.action}")
        print(f"  Reason: {actual_decision.reason}")
        if decision.action == CHANGE_LANE and not lane_change_started:
            print("  Lane change unavailable: max_spostamenti reached.")

    def _cancel_pending_decision(self) -> None:
        if hasattr(self, "llm_decision_engine"):
            self.llm_decision_engine.cancel()
        self.pending_world_context = None
        self.decision_phase = DRIVING

    def _stop(self, _event: arcade.gui.UIOnClickEvent) -> None:
        self.world.reset()
        self.world.configure_vehicle(
            vision_distance=self.vision_distance,
            decision_distance=self.decision_distance,
            max_spostamenti=self.max_spostamenti,
        )
        self.world.cars[0].speed = self.scenario_initial_speeds[self.current_scenario]
        self._reset_run_state()

    def _show_simulation_end(self) -> None:
        self.is_running = False
        self.simulation_finished = True
        self.decision_phase = DRIVING
        self.manager.clear()
        self._setup_simulation_end_actions()

    def _setup_simulation_end_actions(self) -> None:
        panel_height = 350
        report_button = arcade.gui.UIFlatButton(
            text="Report",
            width=160,
            height=42,
            style=REPORT_BUTTON_STYLE,
        )
        report_button.on_click = self._open_report
        reset_button = arcade.gui.UIFlatButton(
            text="Reset",
            width=160,
            height=42,
            style=arcade.gui.UIFlatButton.STYLE_BLUE,
        )
        reset_button.on_click = self._reset_from_end
        anchor = arcade.gui.UIAnchorLayout()
        anchor.add(
            report_button,
            anchor_x="center",
            anchor_y="center",
            align_x=-88,
            align_y=-panel_height / 2 + 54,
        )
        anchor.add(
            reset_button,
            anchor_x="center",
            anchor_y="center",
            align_x=88,
            align_y=-panel_height / 2 + 54,
        )
        self.manager.add(anchor)

    def _reset_from_end(self, event: arcade.gui.UIOnClickEvent) -> None:
        self.active_screen = "simulation"
        self._stop(event)
        self.manager.clear()
        self._setup_toolbar()

    @staticmethod
    def _casualty_category_counts(
        dead: list[Pedestrian],
    ) -> dict[str, int]:
        counts = {"Child": 0, "Adult": 0, "Elderly": 0}
        for person in dead:
            if person.model in {"boy", "girl"}:
                category = "Child"
            elif person.model in {"old_man", "old_woman"}:
                category = "Elderly"
            elif person.model == "custom":
                category = "Custom"
            else:
                category = "Adult"
            counts[category] = counts.get(category, 0) + 1
        return counts

    def _build_report_data(self) -> SimulationReportData:
        dead = self.world.dead_pedestrians()
        casualties = [
            {"model": person.model, "label": person.label}
            for person in dead
        ]
        framework = self.ethical_frameworks.get(self.current_framework)
        history = list(framework.decision_history) if framework is not None else []
        metrics = framework.summary(casualties) if framework is not None else []
        return SimulationReportData(
            framework_name=self.current_framework,
            implementation=self.current_implementation,
            total_deaths=len(dead),
            lane_changes_used=self.world.lane_changes_used,
            max_lane_changes=self.world.max_spostamenti,
            casualty_counts=self._casualty_category_counts(dead),
            decision_history=history,
            framework_metrics=metrics,
        )

    def _open_report(
        self,
        _event: arcade.gui.UIOnClickEvent | None = None,
    ) -> None:
        if not self.simulation_finished:
            return
        self.active_screen = "report"
        self.report_page = 0
        self._setup_report_navigation()

    def _setup_report_navigation(self) -> None:
        data = self._build_report_data()
        page_count = self.report_renderer.page_count(data, self.height)
        self.report_page = max(0, min(self.report_page, page_count - 1))
        self.manager.clear()
        build_report_navigation(
            self.manager,
            page=self.report_page,
            page_count=page_count,
            on_previous=self._previous_report_page,
            on_next=self._next_report_page,
            on_back=self._back_to_summary,
            on_restart=self._reset_from_end,
        )

    def _previous_report_page(
        self,
        _event: arcade.gui.UIOnClickEvent | None = None,
    ) -> None:
        self.report_page = max(0, self.report_page - 1)
        self._setup_report_navigation()

    def _next_report_page(
        self,
        _event: arcade.gui.UIOnClickEvent | None = None,
    ) -> None:
        page_count = self.report_renderer.page_count(
            self._build_report_data(),
            self.height,
        )
        self.report_page = min(page_count - 1, self.report_page + 1)
        self._setup_report_navigation()

    def _back_to_summary(
        self,
        _event: arcade.gui.UIOnClickEvent | None = None,
    ) -> None:
        self.active_screen = "simulation"
        self.manager.clear()
        self._setup_simulation_end_actions()

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
            else "Utilitarianism"
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
            utilitarian_entity_values=self.framework_settings["Utilitarianism"],
            kant_rules=self._framework_rule_rows("Kant"),
            constant_rules=self._framework_rule_rows("Constant"),
            constant_conflict_resolution=self.framework_settings["Constant"][
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
            if framework_name == "Kant"
            else list(DEFAULT_RULE_ORDER)
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
        rule_order = self.framework_settings["Kant"]["rule_order"]
        current_index = rule_order.index(rule_key)
        target_index = max(0, min(len(rule_order) - 1, current_index + direction))
        if target_index == current_index:
            return
        rule_order[current_index], rule_order[target_index] = (
            rule_order[target_index],
            rule_order[current_index],
        )
        self._apply_framework_rule_settings("Kant")
        self._show_framework_editor("Kant")

    def _set_constant_conflict_resolver(self, resolver: str) -> None:
        self.framework_settings["Constant"]["conflict_resolution"] = resolver
        self._apply_framework_rule_settings("Constant")
        self._show_framework_editor("Constant")

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
            self.framework_status_label.text = "Enter a valid numeric value in every field."
            return

        self.framework_settings["Utilitarianism"].update(parsed_values)
        utilitarian = self.ethical_frameworks["Utilitarianism"]
        utilitarian.update_entity_values(parsed_values)
        constant = self.ethical_frameworks["Constant"]
        constant.update_entity_values(parsed_values)
        self.framework_status_label.text = "Values saved in simulation state."

    def _open_scenario_settings(
        self, _event: arcade.gui.UIOnClickEvent | None = None
    ) -> None:
        self.scenario_editor_draft = deepcopy(self.scenario_definitions)
        self.scenario_editor_scenario = self.current_scenario
        self.scenario_editor_entity = ("cars", 0)
        self.scenario_editor_message = ""
        self._show_scenario_editor()

    def _show_scenario_editor(self) -> None:
        self.active_screen = "scenario_settings"
        self.manager.clear()
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
            scenario_names=list(self.scenario_editor_draft),
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

    def _commit_scenario_entity_form(self) -> bool:
        """Copy the visible form into the in-memory editor draft."""
        entity_kind, entity_index = self.scenario_editor_entity
        entity = self.scenario_editor_draft[self.scenario_editor_scenario][entity_kind][
            entity_index
        ]
        original_entity = dict(entity)

        def number(key: str, label: str, *, minimum: float | None = None) -> float | None:
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
            speed_kmh = number("speed_kmh", "Speed", minimum=0.1)
            if speed_kmh is None:
                return False
            entity.update({"speed": speed_kmh / 0.18})
        else:
            selected_label = (
                self.scenario_editor_model.value
                if self.scenario_editor_model is not None
                else "Man"
            )
            model = next(
                (
                    key
                    for key, display_name in ENTITY_MODEL_LABELS.items()
                    if display_name == selected_label
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
                else 55.0
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

    def _select_scenario_to_edit(self, scenario_name: str) -> None:
        if not self._commit_scenario_entity_form():
            return
        self.scenario_editor_scenario = scenario_name
        self.scenario_editor_entity = ("cars", 0)
        self._show_scenario_editor()

    def _select_scenario_entity(self, entity_kind: str, entity_index: int) -> None:
        if not self._commit_scenario_entity_form():
            return
        self.scenario_editor_entity = (entity_kind, entity_index)
        self._show_scenario_editor()

    def _add_scenario_car(
        self, _event: arcade.gui.UIOnClickEvent | None = None
    ) -> None:
        if not self._commit_scenario_entity_form():
            return
        cars = self.scenario_editor_draft[self.scenario_editor_scenario]["cars"]
        cars.append(
            {
                "x": 130.0 + 110.0 * len(cars),
                "y_offset": -45.0,
                "speed": 120.0,
            }
        )
        self.scenario_editor_entity = ("cars", len(cars) - 1)
        self.scenario_editor_message = "Car added. Save to make it persistent."
        self._show_scenario_editor()

    def _add_scenario_pedestrian(
        self, _event: arcade.gui.UIOnClickEvent | None = None
    ) -> None:
        if not self._commit_scenario_entity_form():
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
                "speed": 55.0,
            }
        )
        self.scenario_editor_entity = ("pedestrians", len(pedestrians) - 1)
        self.scenario_editor_message = "Pedestrian added. Save to make it persistent."
        self._show_scenario_editor()

    def _open_scenario_location_picker(
        self, _event: arcade.gui.UIOnClickEvent | None = None
    ) -> None:
        if not self._commit_scenario_entity_form():
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
        entities = self.scenario_editor_draft[self.scenario_editor_scenario][entity_kind]
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
        if not self._commit_scenario_entity_form():
            return
        try:
            saved_definitions = save_scenario_definitions(
                self.scenario_editor_draft
            )
        except (OSError, ValueError) as error:
            self._set_scenario_editor_error(f"Could not save scenarios: {error}")
            return

        self.scenario_definitions = saved_definitions
        self.scenario_editor_draft = deepcopy(saved_definitions)
        self.scenario_names = list(saved_definitions)
        self.scenario_initial_speeds = {
            name: float(definition["cars"][0]["speed"])
            for name, definition in saved_definitions.items()
        }
        self.world.set_scenario_definitions(saved_definitions)
        self.world.reset(self.current_scenario)
        self.world.configure_vehicle(
            vision_distance=self.vision_distance,
            decision_distance=self.decision_distance,
            max_spostamenti=self.max_spostamenti,
        )
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

    @staticmethod
    def _open_repository(_event: arcade.gui.UIOnClickEvent | None = None) -> None:
        webbrowser.open(GITHUB_REPOSITORY)

    def on_update(self, delta_time: float) -> None:
        if self.active_screen != "simulation":
            return

        if not self.is_running:
            return

        if self.decision_phase == WAITING_FOR_LLM:
            # Virtual time is intentionally frozen while the provider works.
            self._poll_llm_decision()
            return

        scaled_delta_time = delta_time * self.time_scale
        if self.decision_phase == DRIVING:
            self._maybe_trigger_ethical_decision()
            if self.decision_phase == WAITING_FOR_LLM:
                return

        reached_tunnel = self.world.update(scaled_delta_time)
        car = self.world.primary_car
        if (
            self.decision_phase == EXECUTING_DECISION
            and (car is None or not car.is_changing_lane)
        ):
            self.decision_phase = DRIVING
        if reached_tunnel and not self.simulation_finished:
            self._show_simulation_end()

    def on_draw(self) -> None:
        self.clear()
        if self.active_screen == "scenario_location_picker":
            if self.scenario_location_preview is not None:
                self.scenario_location_preview.draw(show_vehicle_vision=False)
            cursor_x, cursor_y = self.scenario_location_cursor
            if cursor_y < self.height - 78:
                entity_kind, _entity_index = self.scenario_editor_entity
                entity_top_offset = 34 if entity_kind == "cars" else 22
                arrow_tip_y = cursor_y + entity_top_offset
                arrow_base_y = arrow_tip_y + 12
                marker_color = (190, 145, 25)
                arcade.draw_line(
                    cursor_x,
                    arrow_base_y + 22,
                    cursor_x,
                    arrow_base_y,
                    marker_color,
                    3,
                )
                arcade.draw_triangle_filled(
                    cursor_x - 7,
                    arrow_base_y,
                    cursor_x + 7,
                    arrow_base_y,
                    cursor_x,
                    arrow_tip_y,
                    marker_color,
                )
                self.scenario_location_text.x = cursor_x
                self.scenario_location_text.y = arrow_base_y + 27
                self.scenario_location_text.draw()
                arcade.draw_circle_outline(
                    cursor_x,
                    cursor_y,
                    15,
                    (42, 177, 230),
                    2,
                    num_segments=32,
                )
                arcade.draw_line(
                    cursor_x - 21,
                    cursor_y,
                    cursor_x + 21,
                    cursor_y,
                    (42, 177, 230),
                    2,
                )
                arcade.draw_line(
                    cursor_x,
                    cursor_y - 21,
                    cursor_x,
                    cursor_y + 21,
                    (42, 177, 230),
                    2,
                )
            self.manager.draw()
            return
        if self.active_screen == "report":
            self.report_renderer.draw(
                self.width,
                self.height,
                self._build_report_data(),
                self.report_page,
            )
            self.manager.draw()
            return
        if self.active_screen != "simulation":
            self._draw_navigation_background()
            self.manager.draw()
            return

        self.world.draw()
        arcade.draw_lbwh_rectangle_filled(
            0, self.height - TOOLBAR_HEIGHT, self.width, TOOLBAR_HEIGHT, (31, 38, 48)
        )
        arcade.draw_line(
            0,
            self.height - TOOLBAR_HEIGHT,
            self.width,
            self.height - TOOLBAR_HEIGHT,
            (80, 91, 105),
            2,
        )
        self._draw_vehicle_perception()
        self._draw_vehicle_hud()
        if self.decision_phase == WAITING_FOR_LLM:
            self._draw_llm_loading_overlay()
        if self.simulation_finished:
            self._draw_simulation_end_overlay()
        self.manager.draw()

    def _draw_navigation_background(self) -> None:
        arcade.draw_lbwh_rectangle_filled(
            0, 0, self.width, self.height, (23, 30, 39)
        )
        panel_width = min(980, self.width - 80)
        panel_height = min(650, self.height - 80)
        panel_left = (self.width - panel_width) / 2
        panel_bottom = (self.height - panel_height) / 2
        arcade.draw_lbwh_rectangle_filled(
            panel_left,
            panel_bottom,
            panel_width,
            panel_height,
            (31, 38, 48),
        )
        arcade.draw_lbwh_rectangle_outline(
            panel_left,
            panel_bottom,
            panel_width,
            panel_height,
            (78, 96, 115),
            1,
        )
        arcade.draw_lbwh_rectangle_filled(
            panel_left, panel_bottom + panel_height - 4, panel_width, 4, (42, 177, 230)
        )

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if self.active_screen != "simulation":
            if symbol == arcade.key.ESCAPE:
                if self.active_screen == "scenario_location_picker":
                    self._cancel_scenario_location_picker()
                elif self.active_screen == "report":
                    self._back_to_summary()
                elif self.active_screen == "menu":
                    self._return_to_simulation()
                else:
                    self._open_menu()

    def on_mouse_motion(
        self,
        x: int,
        y: int,
        dx: int,
        dy: int,
    ) -> None:
        if self.active_screen == "scenario_location_picker":
            entity_kind, entity_index = self.scenario_editor_entity
            margin = 40.0 if entity_kind == "cars" else 12.0
            bounded_x = min(max(float(x), margin), self.width - margin)
            if entity_kind == "cars":
                bounded_y = min(self.world.lane_centers, key=lambda lane_y: abs(y - lane_y))
            else:
                bounded_y = min(max(float(y), margin), self.height - 84.0)
            self.scenario_location_cursor = (bounded_x, bounded_y)
            if self.scenario_location_preview is not None:
                preview_entities = (
                    self.scenario_location_preview.cars
                    if entity_kind == "cars"
                    else self.scenario_location_preview.pedestrians
                )
                preview_entities[entity_index].x = bounded_x
                preview_entities[entity_index].y = bounded_y
                if entity_kind == "cars":
                    preview_entities[entity_index].lane_index = (
                        1 if bounded_y > self.world.road_y else 0
                    )

    def on_mouse_press(
        self,
        x: int,
        y: int,
        button: int,
        modifiers: int,
    ) -> None:
        if (
            self.active_screen != "scenario_location_picker"
            or button != arcade.MOUSE_BUTTON_LEFT
            or y >= self.height - 78
        ):
            return

        entity_kind, entity_index = self.scenario_editor_entity
        margin = 40.0 if entity_kind == "cars" else 12.0
        bounded_x = min(max(float(x), margin), self.width - margin)
        if entity_kind == "cars":
            bounded_y = min(self.world.lane_centers, key=lambda lane_y: abs(y - lane_y))
        else:
            bounded_y = min(max(float(y), margin), self.height - 84.0)
        entity = self.scenario_editor_draft[self.scenario_editor_scenario][entity_kind][
            entity_index
        ]
        entity["x"] = bounded_x
        entity["y_offset"] = (
            45.0 if entity_kind == "cars" and bounded_y > self.world.road_y
            else -45.0 if entity_kind == "cars"
            else bounded_y - self.world.road_y
        )
        self.scenario_editor_message = (
            f"Location set to X {bounded_x:.0f}, Y {bounded_y:.0f}. "
            "Save to make it persistent."
        )
        self.scenario_location_preview = None
        self._show_scenario_editor()

    @staticmethod
    def _create_hud_texts() -> dict[str, arcade.Text]:
        def text(
            font_size: int,
            *,
            anchor_x: str = "left",
            bold: bool = False,
        ) -> arcade.Text:
            return arcade.Text(
                "",
                0,
                0,
                (238, 243, 248),
                font_size,
                anchor_x=anchor_x,
                anchor_y="center",
                bold=bold,
            )

        return {
            "title": text(11, bold=True),
            "speed": text(28, anchor_x="right", bold=True),
            "unit": text(10),
            "lane": text(10, bold=True),
            "changes": text(10),
            "vision": text(9),
            "decision": text(9),
            "last_action": text(9, bold=True),
        }

    def _set_hud_text(self, name: str, content: str, x: float, y: float) -> None:
        text = self._hud_texts[name]
        text.text = content
        text.x = x
        text.y = y
        text.draw()

    @staticmethod
    def _create_perception_texts() -> dict[str, arcade.Text]:
        texts = {
            "title": arcade.Text("", 0, 0, (238, 243, 248), 11, bold=True),
            "subtitle": arcade.Text("", 0, 0, (155, 170, 185), 8),
            "status": arcade.Text("", 0, 0, (238, 243, 248), 10, bold=True),
        }
        for index in range(7):
            texts[f"detail_{index}"] = arcade.Text(
                "", 0, 0, (210, 218, 226), 9
            )
        return texts

    @staticmethod
    def _create_end_texts() -> dict[str, arcade.Text]:
        texts = {
            "title": arcade.Text(
                "",
                0,
                0,
                (238, 243, 248),
                20,
                anchor_x="center",
                anchor_y="center",
                bold=True,
            ),
            "status": arcade.Text(
                "",
                0,
                0,
                (238, 243, 248),
                14,
                anchor_x="center",
                anchor_y="center",
                bold=True,
            ),
            "hint": arcade.Text(
                "",
                0,
                0,
                (155, 170, 185),
                9,
                anchor_x="center",
                anchor_y="center",
            ),
        }
        for index in range(20):
            texts[f"detail_{index}"] = arcade.Text(
                "",
                0,
                0,
                (210, 218, 226),
                10,
                anchor_y="center",
            )
        return texts

    @staticmethod
    def _create_llm_loading_texts() -> dict[str, arcade.Text]:
        return {
            "title": arcade.Text(
                "ANALYZING ETHICAL DILEMMA...",
                0,
                0,
                (255, 237, 170),
                14,
                anchor_x="center",
                anchor_y="center",
                bold=True,
            ),
            "subtitle": arcade.Text(
                "",
                0,
                0,
                (203, 213, 225),
                9,
                anchor_x="center",
                anchor_y="center",
            ),
        }

    def _draw_llm_loading_overlay(self) -> None:
        panel_width = 430.0
        panel_height = 96.0
        left = (self.width - panel_width) / 2
        bottom = (self.height - panel_height) / 2
        arcade.draw_lbwh_rectangle_filled(
            left,
            bottom,
            panel_width,
            panel_height,
            (24, 32, 42, 242),
        )
        arcade.draw_lbwh_rectangle_outline(
            left,
            bottom,
            panel_width,
            panel_height,
            (249, 166, 35),
            2,
        )
        title = self._llm_loading_texts["title"]
        title.x, title.y = self.width / 2, bottom + 60
        title.draw()
        subtitle = self._llm_loading_texts["subtitle"]
        subtitle.text = (
            f"{self.current_framework} · {self.llm_decision_engine.model_name} "
            "· simulation time paused"
        )
        subtitle.x, subtitle.y = self.width / 2, bottom + 31
        subtitle.draw()

    def _draw_simulation_end_overlay(self) -> None:
        dead = self.world.dead_pedestrians()
        panel_width = 520
        panel_height = 350
        panel_left = (self.width - panel_width) / 2
        panel_bottom = (self.height - panel_height) / 2
        panel_top = panel_bottom + panel_height
        center_x = self.width / 2

        arcade.draw_lbwh_rectangle_filled(
            0,
            0,
            self.width,
            self.height,
            (5, 9, 14, 155),
        )
        arcade.draw_lbwh_rectangle_filled(
            panel_left,
            panel_bottom,
            panel_width,
            panel_height,
            (24, 32, 42, 250),
        )
        arcade.draw_lbwh_rectangle_outline(
            panel_left,
            panel_bottom,
            panel_width,
            panel_height,
            (90, 106, 124),
            2,
        )

        title = self._end_texts["title"]
        title.text = "SIMULATION COMPLETE"
        title.x, title.y = center_x, panel_top - 38
        title.draw()

        status = self._end_texts["status"]
        if dead:
            status.text = f"Tunnel reached · Victims: {len(dead)}"
            status.color = (238, 68, 68)
        else:
            status.text = "Tunnel reached · Success nobody is dead!"
            status.color = (79, 196, 123)
        status.x, status.y = center_x, panel_top - 72
        status.draw()

        category_counts = self._casualty_category_counts(dead)

        summary_lines = [
            (
                f"Lane changes: {self.world.lane_changes_used} / "
                f"{self.world.max_spostamenti}"
            ),
            f"Child: {category_counts['Child']}",
            f"Adult: {category_counts['Adult']}",
            f"Elderly: {category_counts['Elderly']}",
        ]
        if category_counts.get("Custom", 0):
            summary_lines.append(f"Custom: {category_counts['Custom']}")
        summary_lines.append(f"Framework: {self.current_framework}")
        summary_lines.append(
            "Implementation: "
            + (
                "LLM Agent"
                if self.current_implementation == LLM_MODE
                else "Code"
            )
        )

        framework = self.ethical_frameworks.get(self.current_framework)
        casualties = [
            {"model": person.model, "label": person.label}
            for person in dead
        ]
        if framework is not None:
            summary_lines.extend(
                f"{label}: {value}"
                for label, value in framework.summary(casualties)
            )

        for index, line in enumerate(summary_lines):
            detail = self._end_texts[f"detail_{index}"]
            detail.text = line
            detail.x = panel_left + 58
            detail.y = panel_top - 108 - index * 22
            detail.draw()

        hint = self._end_texts["hint"]
        hint.text = "Open the report or reset to start a new simulation."
        hint.x, hint.y = center_x, panel_bottom + 24
        hint.draw()

    def _set_perception_text(
        self,
        name: str,
        content: str,
        x: float,
        y: float,
        color: tuple[int, int, int] | None = None,
    ) -> None:
        text = self._perception_texts[name]
        text.text = content
        text.x = x
        text.y = y
        if color is not None:
            text.color = color
        text.draw()

    @staticmethod
    def _demographic_lines(casualties: list[Pedestrian]) -> list[str]:
        labels = {
            "man": "Adult (M)",
            "woman": "Adult (F)",
            "old_man": "Senior (M)",
            "old_woman": "Senior (F)",
            "boy": "Child (M)",
            "girl": "Child (F)",
            "custom": "Custom",
        }
        counts: dict[str, int] = {}
        for pedestrian in casualties:
            label = labels[pedestrian.model]
            counts[label] = counts.get(label, 0) + 1

        if not counts:
            return ["No visible entities"]
        return [f"{label}: {count}" for label, count in counts.items()]

    def _draw_vehicle_perception(self) -> None:
        current_entities, other_entities = self.world.visible_lane_entities()
        incident_distance = self.world.next_incident_distance()
        panel_left = 14
        panel_width = 300
        panel_height = 250
        panel_top = self.height - TOOLBAR_HEIGHT - 14
        panel_bottom = panel_top - panel_height
        content_left = panel_left + 16
        decision_due = (
            incident_distance is not None
            and incident_distance <= self.world.decision_distance
        )
        accent = (238, 68, 68) if decision_due else (42, 177, 230)

        arcade.draw_lbwh_rectangle_filled(
            panel_left,
            panel_bottom,
            panel_width,
            panel_height,
            (18, 24, 32, 232),
        )
        arcade.draw_lbwh_rectangle_outline(
            panel_left,
            panel_bottom,
            panel_width,
            panel_height,
            (78, 96, 115),
            1,
        )
        arcade.draw_lbwh_rectangle_filled(panel_left, panel_top - 4, panel_width, 4, accent)
        self._set_perception_text(
            "title",
            "VEHICLE PERCEPTION",
            content_left,
            panel_top - 26,
        )
        self._set_perception_text(
            "subtitle",
            (
                f"VISION {self.world.vision_distance:.0f}px  ·  "
                f"DECISION {self.world.decision_distance:.0f}px"
            ),
            content_left,
            panel_top - 43,
        )
        card_top = panel_top - 58
        card_bottom = panel_bottom + 15
        card_color = (69, 30, 35, 235) if decision_due else (25, 43, 55, 235)
        arcade.draw_lbwh_rectangle_filled(
            content_left,
            card_bottom,
            panel_width - 32,
            card_top - card_bottom,
            card_color,
        )
        arcade.draw_lbwh_rectangle_filled(
            content_left, card_bottom, 4, card_top - card_bottom, accent
        )
        if incident_distance is None:
            status = "CURRENT LANE CLEAR"
        elif decision_due:
            status = f"DECISION ZONE · {incident_distance:.0f}px"
        else:
            status = f"TRACKING INCIDENT · {incident_distance:.0f}px"
        self._set_perception_text(
            "status",
            status,
            content_left + 13,
            card_top - 25,
            accent,
        )

        details = [f"Current lane: {len(current_entities)}"]
        details.extend(f"  {line}" for line in self._demographic_lines(current_entities))
        details.append(f"Adjacent lane: {len(other_entities)}")
        details.extend(f"  {line}" for line in self._demographic_lines(other_entities))
        for index, detail in enumerate(details[:7]):
            self._set_perception_text(
                f"detail_{index}",
                detail,
                content_left + 13,
                card_top - 51 - index * 18,
                (210, 218, 226),
            )

    def _draw_vehicle_hud(self) -> None:
        car = self.world.cars[0]
        speed_kmh = car.speed * 0.18

        panel_width = 278
        panel_height = 258
        panel_left = self.width - panel_width - 14
        panel_bottom = self.height - TOOLBAR_HEIGHT - panel_height - 14
        panel_top = panel_bottom + panel_height
        content_left = panel_left + 18
        content_right = panel_left + panel_width - 18

        arcade.draw_lbwh_rectangle_filled(
            panel_left,
            panel_bottom,
            panel_width,
            panel_height,
            (18, 24, 32, 232),
        )
        arcade.draw_lbwh_rectangle_outline(
            panel_left,
            panel_bottom,
            panel_width,
            panel_height,
            (78, 96, 115),
            1,
        )
        arcade.draw_lbwh_rectangle_filled(
            panel_left,
            panel_top - 4,
            panel_width,
            4,
            (42, 177, 230),
        )

        self._set_hud_text("title", "VEHICLE STATUS", content_left, panel_top - 25)
        self._set_hud_text("speed", f"{speed_kmh:04.1f}", content_right - 47, panel_top - 65)
        self._set_hud_text("unit", "km/h", content_right - 39, panel_top - 65)

        speed_bar_y = panel_top - 93
        speed_bar_width = panel_width - 36
        speed_ratio = min(speed_kmh / 50.0, 1.0)
        arcade.draw_lbwh_rectangle_filled(
            content_left, speed_bar_y, speed_bar_width, 8, (50, 61, 73)
        )
        arcade.draw_lbwh_rectangle_filled(
            content_left,
            speed_bar_y,
            speed_bar_width * speed_ratio,
            8,
            (42, 177, 230),
        )

        lane_name = "UPPER" if car.lane_index == 1 else "LOWER"
        target_lane_name = "LOWER" if car.lane_index == 1 else "UPPER"
        lane_status = (
            f"LANE  CHANGING TO {target_lane_name}"
            if car.is_changing_lane
            else f"LANE  {lane_name}"
        )
        self._set_hud_text("lane", lane_status, content_left, panel_top - 119)
        self._set_hud_text(
            "changes",
            (
                f"LANE CHANGES  {self.world.lane_changes_used} / "
                f"{self.world.max_spostamenti}"
            ),
            content_left,
            panel_top - 145,
        )
        self._set_hud_text(
            "vision",
            f"VISION DISTANCE  {self.world.vision_distance:.0f} px",
            content_left,
            panel_top - 171,
        )
        self._set_hud_text(
            "decision",
            f"DECISION DISTANCE  {self.world.decision_distance:.0f} px",
            content_left,
            panel_top - 195,
        )
        last_action = self.last_decision.action if self.last_decision else "WAITING"
        action_color = (
            (245, 170, 55)
            if last_action == CHANGE_LANE
            else (79, 196, 123)
        )
        self._hud_texts["last_action"].color = action_color
        self._set_hud_text(
            "last_action",
            f"LAST DECISION  {last_action}",
            content_left,
            panel_top - 226,
        )

    def on_resize(self, width: int, height: int) -> None:
        super().on_resize(width, height)
        # Arcade may dispatch an initial resize while Window is being constructed.
        if hasattr(self, "world"):
            self.world.resize(width, height)
        preview = getattr(self, "scenario_location_preview", None)
        if preview is not None:
            old_preview_road_y = preview.road_y
            preview.resize(width, height)
            cursor_x, cursor_y = self.scenario_location_cursor
            self.scenario_location_cursor = (
                cursor_x,
                cursor_y + preview.road_y - old_preview_road_y,
            )
        if getattr(self, "active_screen", None) == "report":
            self._setup_report_navigation()

    def on_close(self) -> None:
        self.llm_decision_engine.close()
        self.manager.disable()
        super().on_close()


def main() -> None:
    SimulationWindow()
    arcade.run()


if __name__ == "__main__":
    main()
