from __future__ import annotations

import time
import unittest

from automated import (
    COMPARISON,
    ONLY_DETERMINISTIC,
    AutomatedSimulationRunner,
    BatchConfig,
    BatchReport,
    BatchSimulationResult,
)
from decision_engine import LLMDecisionEngine
from ethics.utilitarian import DEFAULT_ENTITIES_VALUES
from llm.base_client import LLMClient
from llm.prompt_builder import PromptBuilder
from llm.schemas import LLMRawResponse, PromptPackage


SCENARIOS = {
    "Batch Test": {
        "cars": [{"x": 100.0, "y_offset": -45.0, "speed": 50.0}],
        "pedestrians": [
            {
                "x": 400.0,
                "y_offset": -45.0,
                "model": "boy",
                "label": None,
                "action": "still",
                "speed": 0.0,
            },
            {
                "x": 400.0,
                "y_offset": 45.0,
                "model": "man",
                "label": None,
                "action": "still",
                "speed": 0.0,
            },
        ],
    }
}


class StayOrChangeClient(LLMClient):
    @property
    def model_name(self) -> str:
        return "batch-fake"

    def generate(
        self,
        prompt: PromptPackage,
        *,
        timeout_seconds: float,
    ) -> LLMRawResponse:
        return LLMRawResponse(
            text=(
                '{"action":"CHANGE_LANE",'
                '"reason":"The other lane has lower malus."}'
            ),
            model=self.model_name,
        )


def config(number_of_runs: int = 2) -> BatchConfig:
    return BatchConfig(
        mode=ONLY_DETERMINISTIC,
        number_of_runs=number_of_runs,
        framework_name="Utilitarianism",
        scenario_name="Batch Test",
        random_seed=100,
        scenario_definitions=SCENARIOS,
        framework_settings={"entity_values": dict(DEFAULT_ENTITIES_VALUES)},
        utilitarian_values=dict(DEFAULT_ENTITIES_VALUES),
        additional_instructions="",
        world_width=700,
        world_height=600,
        vision_distance=300,
        decision_distance=120,
        max_lane_changes=2,
    )


class AutomatedSimulationTests(unittest.TestCase):
    def test_deterministic_batch_runs_in_background_and_aggregates(self) -> None:
        runner = AutomatedSimulationRunner()
        self.addCleanup(runner.close)
        runner.start(config())
        deadline = time.monotonic() + 2
        while runner.is_running and time.monotonic() < deadline:
            time.sleep(0.002)
        report = runner.poll_report()

        self.assertIsNotNone(report)
        assert report is not None
        self.assertEqual(2, report.total_simulations)
        self.assertEqual([100, 101], [result.seed for result in report.results])
        self.assertEqual(1.0, report.average_deaths)
        self.assertEqual(1.0, sum(report.average_deaths_by_entity.values()))
        self.assertEqual(1.0, report.average_deaths_by_entity["man"])
        self.assertEqual({1: 2}, report.lane_change_distribution)
        self.assertTrue(all(result.decision_history for result in report.results))

    def test_paired_runner_reuses_the_same_seed_for_code_and_llm(self) -> None:
        runner = AutomatedSimulationRunner(
            llm_engine_factory=lambda: LLMDecisionEngine(
                client=StayOrChangeClient(),
                prompt_builder=PromptBuilder(),
                timeout_seconds=0.1,
                max_attempts=1,
            )
        )
        self.addCleanup(runner.close)
        paired_config = BatchConfig(
            **{
                **config(1).__dict__,
                "mode": COMPARISON,
            }
        )
        runner.start(paired_config)
        deadline = time.monotonic() + 2
        while runner.is_running and time.monotonic() < deadline:
            time.sleep(0.002)
        report = runner.poll_report()

        self.assertIsNotNone(report)
        assert report is not None
        self.assertEqual(2, report.total_simulations)
        self.assertEqual({100}, {result.seed for result in report.results})
        self.assertEqual(
            {"code", "llm-agent"},
            {result.implementation for result in report.results},
        )
        self.assertEqual(100.0, report.decision_agreement_rate)

    def test_comparison_report_calculates_agreement_and_outcome_changes(self) -> None:
        common = dict(
            framework="Utilitarianism",
            scenario="Batch Test",
            seed=42,
            deaths_by_category={"Child": 0, "Adult": 1, "Elderly": 0},
            lane_changes_used=1,
            max_lane_changes=2,
            number_of_decisions=2,
            framework_specific_metrics={},
            pair_id=1,
        )
        code = BatchSimulationResult(
            implementation="code",
            total_deaths=1,
            deaths_by_entity={"man": 1},
            decision_history=[{"action": "STAY"}, {"action": "CHANGE_LANE"}],
            **common,
        )
        llm = BatchSimulationResult(
            implementation="llm-agent",
            total_deaths=1,
            deaths_by_entity={"woman": 1},
            decision_history=[{"action": "STAY"}, {"action": "STAY"}],
            total_llm_calls=3,
            failed_calls=1,
            retries=1,
            fallbacks=0,
            **common,
        )
        report = BatchReport(
            mode=COMPARISON,
            requested_units=1,
            results=(code, llm),
        )

        self.assertEqual(50.0, report.decision_agreement_rate)
        self.assertEqual(1, report.different_final_results)
        self.assertEqual(3, report.total_llm_calls)
        self.assertEqual(1, report.failed_llm_calls)


if __name__ == "__main__":
    unittest.main()
