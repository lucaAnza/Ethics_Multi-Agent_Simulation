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
                model="gemini-test-model",
                current_lane_count=1,
                other_lane_count=0,
                framework_action="CHANGE_LANE",
                applied_action="CHANGE_LANE",
                reason="The other lane has lower malus.",
                lane_change_blocked=False,
                llm_request="request body",
                llm_response='{"action":"CHANGE_LANE"}',
                llm_raw_response=(
                    '{"candidates":[{"content":{"parts":['
                    '{"text":"raw body"}]}}],'
                    '"response_id":"response-123",'
                    '"usage_metadata":{"prompt_token_count":20,'
                    '"candidates_token_count":5,"total_token_count":25}}'
                ),
            )
            content = log_path.read_text(encoding="utf-8")

        self.assertIn("==================", content)
        self.assertIn("[ETHICAL DECISION] Framework: Utilitarianism", content)
        self.assertIn("  Model: gemini-test-model", content)
        self.assertIn('- LLM-Request : "request body"', content)
        self.assertIn("[ORDERED DECISION]", content)
        self.assertIn("[RAW LLM EXCHANGE]", content)
        self.assertIn('- content-part-text : "raw body"', content)
        self.assertIn('- response_id : "response-123"', content)
        self.assertIn('- prompt_token : "20"', content)
        self.assertIn('- answer_token : "5"', content)
        self.assertIn('- total-token : "25"', content)
        self.assertIn(
            '- LLM-Respond (parsed text) : "{\"action\":\"CHANGE_LANE\"}"',
            content,
        )
        self.assertNotIn("LLM-Respond (raw)", content)
        self.assertIn("============================================", content)

    def test_code_decision_uses_na_for_llm_fields(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            log_path = Path(temporary_directory) / "simulation.log"
            logger = SimulationFileLogger(log_path)
            logger.log_decision(
                framework="Kant",
                implementation="code",
                model=None,
                current_lane_count=1,
                other_lane_count=1,
                framework_action="STAY",
                applied_action="STAY",
                reason="Higher-priority rule selected STAY.",
                lane_change_blocked=False,
                llm_request=None,
                llm_response=None,
                llm_raw_response=None,
            )
            content = log_path.read_text(encoding="utf-8")

        self.assertIn('- LLM-Request : "N/A"', content)
        self.assertIn("  Model: N/A", content)
        self.assertIn('- content-part-text : "N/A"', content)
        self.assertIn('- response_id : "N/A"', content)
        self.assertIn('- prompt_token : "N/A"', content)
        self.assertIn('- answer_token : "N/A"', content)
        self.assertIn('- total-token : "N/A"', content)
        self.assertIn('- LLM-Respond (parsed text) : "N/A"', content)


if __name__ == "__main__":
    unittest.main()
