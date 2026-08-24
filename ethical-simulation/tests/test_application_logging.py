from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app_logging import SimulationFileLogger


class SimulationFileLoggerTests(unittest.TestCase):
    def test_decision_log_contains_summary_and_llm_exchange(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            log_path = Path(temporary_directory) / "simulation.log"
            logger = SimulationFileLogger(log_path)
            logger.log_decision(
                framework="Utilitarianism",
                implementation="llm-agent",
                current_lane_count=1,
                other_lane_count=0,
                framework_action="CHANGE_LANE",
                applied_action="CHANGE_LANE",
                reason="The other lane has lower malus.",
                lane_change_blocked=False,
                llm_request="request body",
                llm_response="response body",
            )
            content = log_path.read_text(encoding="utf-8")

        self.assertIn("==================", content)
        self.assertIn("[ETHICAL DECISION] Framework: Utilitarianism", content)
        self.assertIn('- LLM-Request : "request body"', content)
        self.assertIn('- LLM-Respond : "response body"', content)
        self.assertIn("============================================", content)

    def test_code_decision_uses_na_for_llm_fields(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            log_path = Path(temporary_directory) / "simulation.log"
            logger = SimulationFileLogger(log_path)
            logger.log_decision(
                framework="Kant",
                implementation="code",
                current_lane_count=1,
                other_lane_count=1,
                framework_action="STAY",
                applied_action="STAY",
                reason="Higher-priority rule selected STAY.",
                lane_change_blocked=False,
                llm_request=None,
                llm_response=None,
            )
            content = log_path.read_text(encoding="utf-8")

        self.assertEqual(2, content.count('"N/A"'))


if __name__ == "__main__":
    unittest.main()
