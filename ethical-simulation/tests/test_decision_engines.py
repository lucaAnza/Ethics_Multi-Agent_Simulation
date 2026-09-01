from __future__ import annotations

from pathlib import Path
import time
import unittest

from decision_engine import CodeDecisionEngine, LLMDecisionEngine
from ethics.base import CHANGE_LANE, STAY, DecisionContext
from ethics.utilitarian import UtilitarianFramework
from ethics.virtue import VirtueEthicsFramework
from llm.base_client import LLMClient
from llm.errors import safe_error_message
from llm.parser import InvalidLLMResponse, parse_decision
from llm.prompt_builder import PromptBuilder
from llm.schemas import LLMRawResponse, PromptPackage


class FakeClient(LLMClient):
    def __init__(self, responses: list[str | Exception]) -> None:
        self.responses = list(responses)
        self.calls = 0

    @property
    def model_name(self) -> str:
        return "fake-flash"

    def generate(
        self,
        prompt: PromptPackage,
        *,
        timeout_seconds: float,
    ) -> LLMRawResponse:
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return LLMRawResponse(
            text=response,
            model=self.model_name,
            raw_response=f"RAW PROVIDER RESPONSE: {response}",
        )


def decision_context() -> DecisionContext:
    return DecisionContext.from_state(
        decision_id=1,
        vehicle_position=1250,
        lane_changes_remaining=1,
        state={
            "current_lane_entities": [{"model": "boy", "distance": 100}],
            "other_lane_entities": [{"model": "man", "distance": 90}],
        },
    )


class DecisionContractTests(unittest.TestCase):
    def test_parser_accepts_only_the_decision_contract(self) -> None:
        decision = parse_decision(
            '{"action":"CHANGE_LANE","reason":"Lower configured malus."}'
        )
        self.assertEqual(CHANGE_LANE, decision.action)
        with self.assertRaises(InvalidLLMResponse):
            parse_decision('{"action":"BRAKE","reason":"Not allowed."}')
        with self.assertRaises(InvalidLLMResponse):
            parse_decision(
                '{"action":"STAY","reason":"Fine","invented_field":true}'
            )

    def test_user_facing_errors_redact_credentials(self) -> None:
        message = safe_error_message(
            "Request failed with api_key=secret-value and token AIzaSecret123"
        )
        self.assertNotIn("secret-value", message)
        self.assertNotIn("AIzaSecret123", message)
        self.assertIn("[REDACTED]", message)

    def test_code_and_prompt_receive_the_same_context(self) -> None:
        context = decision_context()
        framework = UtilitarianFramework({"boy": 30, "man": 10})
        decision = CodeDecisionEngine.decide(framework, context)
        self.assertEqual(CHANGE_LANE, decision.action)
        self.assertEqual("code", decision.details["mode"])

        prompts = PromptBuilder(
            Path(__file__).resolve().parents[1] / "config" / "prompts"
        )
        package = prompts.build(
            framework_name="Utilitarianism",
            framework_settings={"entity_values": {"boy": 30, "man": 10}},
            additional_instructions="Keep the explanation short.",
            context=context,
        )
        for expected in (
            '"decision_id": 1',
            '"vehicle_position": 1250',
            '"lane_changes_remaining": 1',
            '"current_lane_entities"',
            '"other_lane_entities"',
        ):
            self.assertIn(expected, package.prompt)

    def test_virtue_ethics_has_a_dedicated_llm_prompt_and_history(self) -> None:
        context = decision_context()
        prompts = PromptBuilder()
        package = prompts.build(
            framework_name="Virtue Ethics",
            framework_settings={},
            additional_instructions="Prioritize compassion.",
            context=context,
        )
        self.assertIn("practical wisdom", package.prompt)
        self.assertIn("Prioritize compassion.", package.prompt)

        framework = VirtueEthicsFramework()
        decision = parse_decision(
            '{"action":"STAY","reason":"Restraint favors staying."}'
        )
        framework.record_decision(decision, context=context)
        self.assertEqual("STAY", framework.decision_history[0]["action"])


class AsyncLLMEngineTests(unittest.TestCase):
    def _wait_for_result(self, engine: LLMDecisionEngine):
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            result = engine.poll()
            if result is not None:
                return result
            time.sleep(0.005)
        self.fail("The fake LLM decision did not complete")

    def test_invalid_response_is_retried(self) -> None:
        client = FakeClient(
            [
                "not json",
                '{"action":"STAY","reason":"The comparison is tied."}',
            ]
        )
        engine = LLMDecisionEngine(
            client=client,
            prompt_builder=PromptBuilder(),
            timeout_seconds=0.1,
            max_attempts=2,
        )
        self.addCleanup(engine.close)
        self.assertTrue(
            engine.submit(
                framework_name="Utilitarianism",
                framework_settings={"entity_values": {}},
                additional_instructions="",
                context=decision_context(),
            )
        )
        result = self._wait_for_result(engine)
        self.assertEqual(STAY, result.decision.action)
        self.assertEqual(2, result.decision.details["attempts"])
        self.assertFalse(result.decision.details["fallback"])
        self.assertIn("SYSTEM INSTRUCTION", result.llm_request)
        self.assertIn('"action":"STAY"', result.llm_response)
        self.assertIn("RAW PROVIDER RESPONSE", result.llm_raw_response)

    def test_errors_fall_back_to_stay_and_are_recorded(self) -> None:
        client = FakeClient([RuntimeError("offline"), RuntimeError("offline")])
        engine = LLMDecisionEngine(
            client=client,
            prompt_builder=PromptBuilder(),
            timeout_seconds=0.1,
            max_attempts=2,
        )
        self.addCleanup(engine.close)
        engine.submit(
            framework_name="Kant",
            framework_settings={"rule_order": [], "enabled_rules": {}},
            additional_instructions="",
            context=decision_context(),
        )
        result = self._wait_for_result(engine)
        self.assertEqual(STAY, result.decision.action)
        self.assertTrue(result.decision.details["fallback"])
        self.assertEqual("llm-agent", result.decision.details["mode"])
        self.assertIn("offline", result.decision.reason)
        self.assertIn("ERROR: offline", result.llm_response)

        framework = UtilitarianFramework()
        framework.record_decision(result.decision, context=result.context)
        record = framework.decision_history[0]
        self.assertEqual("fake-flash", record["model"])
        self.assertIn("latency_ms", record)
        self.assertTrue(record["fallback"])


if __name__ == "__main__":
    unittest.main()
