"""Concrete Arcade window assembled from focused application mixins."""

from __future__ import annotations

from copy import deepcopy

import arcade
import arcade.gui

from application.automated import AutomatedSimulationMixin
from application.controls import SimulationControlsMixin
from application.events import WindowEventsMixin
from application.framework_settings import FrameworkSettingsMixin
from application.lifecycle import SimulationLifecycleMixin
from application.scenario_editor import ScenarioEditorMixin
from automated import (
    COMPARISON,
    ONLY_DETERMINISTIC,
    ONLY_LLM,
    AutomatedSimulationRunner,
    BatchConfig,
    BatchReport,
)
from automated.config import (
    DEFAULT_COMPARISON_BATCH_SIZE,
    DEFAULT_DETERMINISTIC_BATCH_SIZE,
    DEFAULT_LLM_BATCH_SIZE,
)
from decision_engine import CODE_MODE, DRIVING, DecisionEngineFactory
from ethics.base import EthicalDecision
from ethics.constant import UTILITARIAN_EVALUATION
from ethics.utils.config import (
    CONSTANT,
    DEFAULT_CONSTANT_RULE_ENABLED,
    DEFAULT_ENTITIES_VALUES,
    DEFAULT_KANT_RULE_ENABLED,
    DEFAULT_KANT_RULE_ORDER,
    FRAMEWORKS,
    KANT,
    LLM_FRAMEWORKS,
    UTILITARIANISM,
)
from ethics.utils.factory import EthicalFrameworkFactory
from scenarios import (
    DEFAULT_SCENARIO_NAME,
    RANDOM_SCENARIO_NAME,
    load_scenario_settings,
)
from simulation import SimulationEngine, World
from simulation.config import (
    DEFAULT_DECISION_DISTANCE,
    DEFAULT_MAX_LANE_CHANGES,
    DEFAULT_VISION_DISTANCE,
    DEFAULT_WINDOW_HEIGHT as SCREEN_HEIGHT,
    DEFAULT_WINDOW_WIDTH as SCREEN_WIDTH,
)
from ui.batch_report import BatchReportRenderer
from ui.report import SimulationReportRenderer
from ui.simulation_view import SimulationViewMixin


class SimulationWindow(
    SimulationControlsMixin,
    SimulationLifecycleMixin,
    FrameworkSettingsMixin,
    ScenarioEditorMixin,
    AutomatedSimulationMixin,
    WindowEventsMixin,
    SimulationViewMixin,
    arcade.Window,
):
    """Own application state and compose the interactive client features."""

    def __init__(self) -> None:
        super().__init__(
            SCREEN_WIDTH,
            SCREEN_HEIGHT,
            "Ethical Multi-Agent Simulation",
            resizable=True,
        )
        self.set_minimum_size(1185, 500)
        self._initialize_selection_and_run_state()
        self._initialize_world()
        self._initialize_frameworks()
        self._initialize_scenario_editor()
        self._initialize_reports_and_batch_runner()

        self.manager = arcade.gui.UIManager()
        self._setup_toolbar()
        self.manager.enable()
        arcade.set_background_color((91, 145, 79))

    def _initialize_selection_and_run_state(self) -> None:
        """Load persisted selections and initialize transient run values."""
        self.current_framework = UTILITARIANISM
        self.current_implementation = CODE_MODE
        self.framework_editor_mode = CODE_MODE
        stored_scenario_settings = load_scenario_settings()
        self.scenario_definitions = stored_scenario_settings.definitions
        self.random_scenario_settings = stored_scenario_settings.random_scenario
        self.scenario_names = [*self.scenario_definitions, RANDOM_SCENARIO_NAME]
        self.current_scenario = (
            DEFAULT_SCENARIO_NAME
            if DEFAULT_SCENARIO_NAME in self.scenario_definitions
            else self.scenario_names[0]
        )
        self.active_screen = "simulation"
        self.is_running = False
        self.time_scale = 1.0
        self.vision_distance = DEFAULT_VISION_DISTANCE
        self.decision_distance = DEFAULT_DECISION_DISTANCE
        self.max_spostamenti = DEFAULT_MAX_LANE_CHANGES
        self.fixed_vision_distance = self.vision_distance
        self.fixed_decision_distance = self.decision_distance
        self.fixed_max_spostamenti = self.max_spostamenti
        self.simulation_finished = False
        self.last_decision: EthicalDecision | None = None
        self.decision_phase = DRIVING
        self.decision_sequence = 0

    def _initialize_world(self) -> None:
        """Create the world from the validated scenario catalog."""
        self.world = World(
            self.width,
            self.height,
            self.current_scenario,
            self.scenario_definitions,
            random_scenario_settings=self.random_scenario_settings,
        )
        self.world.configure_vehicle(
            vision_distance=self.vision_distance,
            decision_distance=self.decision_distance,
            max_spostamenti=self.max_spostamenti,
        )

    def _initialize_frameworks(self) -> None:
        """Create framework strategies and the shared decision engine."""
        self.framework_settings = {
            UTILITARIANISM: dict(DEFAULT_ENTITIES_VALUES),
            KANT: {
                "rule_order": list(DEFAULT_KANT_RULE_ORDER),
                "enabled_rules": dict(DEFAULT_KANT_RULE_ENABLED),
            },
            CONSTANT: {
                "enabled_rules": dict(DEFAULT_CONSTANT_RULE_ENABLED),
                "conflict_resolution": UTILITARIAN_EVALUATION,
            },
        }
        self.ethical_frameworks = {
            framework_name: EthicalFrameworkFactory.create(
                framework_name,
                self._framework_configuration(framework_name),
                utilitarian_values=self.framework_settings[UTILITARIANISM],
            )
            for framework_name in FRAMEWORKS
        }
        self.llm_additional_instructions = {
            framework_name: "" for framework_name in sorted(LLM_FRAMEWORKS)
        }
        self.code_decision_engine = DecisionEngineFactory.create_code()
        self.llm_decision_engine = DecisionEngineFactory.create_llm()
        self.simulation_engine = SimulationEngine(
            world=self.world,
            framework_name=self.current_framework,
            implementation=self.current_implementation,
            framework=self.ethical_frameworks[self.current_framework],
            framework_settings_provider=self._framework_configuration,
            additional_instructions_provider=(
                lambda framework_name: self.llm_additional_instructions.get(
                    framework_name,
                    "",
                )
            ),
            code_decision_engine=self.code_decision_engine,
            llm_decision_engine=self.llm_decision_engine,
        )
        self.utilitarian_entity_inputs: dict[str, arcade.gui.UIInputText] = {}
        self.llm_additional_instructions_input: arcade.gui.UIInputText | None = None
        self.framework_status_label: arcade.gui.UILabel | None = None

    def _initialize_scenario_editor(self) -> None:
        """Prepare scenario-editor drafts and widget references."""
        self._refresh_scenario_initial_speeds()
        self.scenario_editor_draft = deepcopy(self.scenario_definitions)
        self.random_scenario_settings_draft = self.random_scenario_settings
        self.scenario_editor_scenario = self.current_scenario
        self.scenario_editor_entity = ("cars", 0)
        self.scenario_editor_inputs: dict[str, arcade.gui.UIInputText] = {}
        self.scenario_editor_model: arcade.gui.UIDropdown | None = None
        self.scenario_editor_action: arcade.gui.UIDropdown | None = None
        self.scenario_editor_pedestrian_speed: arcade.gui.UISlider | None = None
        self.scenario_editor_status: arcade.gui.UILabel | None = None
        self.random_scenario_inputs: dict[str, arcade.gui.UIInputText] = {}
        self.random_scenario_dropdowns: dict[str, arcade.gui.UIDropdown] = {}
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

    def _initialize_reports_and_batch_runner(self) -> None:
        """Prepare renderers and automated-simulation state."""
        self._hud_texts = self._create_hud_texts()
        self._perception_texts = self._create_perception_texts()
        self._end_texts = self._create_end_texts()
        self._llm_loading_texts = self._create_llm_loading_texts()
        self.report_renderer = SimulationReportRenderer()
        self.report_page = 0
        self.automated_runner = AutomatedSimulationRunner()
        self.batch_renderer = BatchReportRenderer()
        self.automated_mode = ONLY_DETERMINISTIC
        self.automated_framework = UTILITARIANISM
        self.automated_scenario = self.current_scenario
        self.automated_counts = {
            ONLY_DETERMINISTIC: str(DEFAULT_DETERMINISTIC_BATCH_SIZE),
            ONLY_LLM: str(DEFAULT_LLM_BATCH_SIZE),
            COMPARISON: str(DEFAULT_COMPARISON_BATCH_SIZE),
        }
        self.automated_seed = ""
        self.automated_count_input: arcade.gui.UIInputText | None = None
        self.automated_seed_input: arcade.gui.UIInputText | None = None
        self.automated_status_label: arcade.gui.UILabel | None = None
        self.automated_cancel_button: arcade.gui.UIFlatButton | None = None
        self.last_batch_config: BatchConfig | None = None
        self.batch_report: BatchReport | None = None

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
        self.automated_runner.close()
        self.simulation_engine.close()
        self.llm_decision_engine.close()
        self.manager.disable()
        super().on_close()
