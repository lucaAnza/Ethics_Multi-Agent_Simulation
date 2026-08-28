from __future__ import annotations

import random
import unittest

from decision_engine import (
    CODE_MODE,
    LLM_MODE,
    CodeDecisionEngine,
    DecisionEngineFactory,
    LLMDecisionEngine,
)
from ethics.utils.config import CONSTANT, KANT, UTILITARIANISM, VIRTUE_ETHICS
from ethics.constant import ConstantFramework
from ethics.utils.factory import EthicalFrameworkFactory
from ethics.kant import KantFramework
from ethics.utilitarian import UtilitarianFramework
from ethics.virtue import VirtueEthicsFramework
from llm import LLMClient, PromptBuilder
from llm.schemas import LLMRawResponse, PromptPackage
from scenarios import ScenarioFactory, create_scenario
from simulation.entities import Car, Pedestrian
from simulation.entity_factory import EntityFactory


class StubClient(LLMClient):
    @property
    def model_name(self) -> str:
        return "factory-test"

    def generate(
        self,
        prompt: PromptPackage,
        *,
        timeout_seconds: float,
    ) -> LLMRawResponse:
        del prompt, timeout_seconds
        return LLMRawResponse(
            text='{"action":"STAY","reason":"Test"}',
            model=self.model_name,
        )


class FactoryMethodTests(unittest.TestCase):
    def test_framework_factory_delegates_to_the_expected_creator(self) -> None:
        expected_types = {
            UTILITARIANISM: UtilitarianFramework,
            KANT: KantFramework,
            CONSTANT: ConstantFramework,
            VIRTUE_ETHICS: VirtueEthicsFramework,
        }
        for framework_name, expected_type in expected_types.items():
            with self.subTest(framework=framework_name):
                framework = EthicalFrameworkFactory.create(framework_name)
                self.assertIsInstance(framework, expected_type)

        first = EthicalFrameworkFactory.create(UTILITARIANISM)
        second = EthicalFrameworkFactory.create(UTILITARIANISM)
        self.assertIsNot(first, second)
        self.assertIsNot(first.decision_history, second.decision_history)

    def test_framework_factory_rejects_unknown_names(self) -> None:
        with self.assertRaises(ValueError):
            EthicalFrameworkFactory.create("Unknown")

    def test_decision_engine_factory_supports_defaults_and_injection(self) -> None:
        code_engine = DecisionEngineFactory.create(CODE_MODE)
        self.assertIsInstance(code_engine, CodeDecisionEngine)

        client = StubClient()
        llm_engine = DecisionEngineFactory.create(
            LLM_MODE,
            client=client,
            prompt_builder=PromptBuilder(),
            timeout_seconds=12,
            max_attempts=1,
        )
        self.assertIsInstance(llm_engine, LLMDecisionEngine)
        self.assertIs(llm_engine.client, client)
        self.assertEqual(12, llm_engine.timeout_seconds)
        llm_engine.close()

        with self.assertRaises(ValueError):
            DecisionEngineFactory.create("unsupported")

    def test_entity_and_scenario_factories_share_one_creation_path(self) -> None:
        car_definition = {"x": 130, "y_offset": -45, "speed": 60}
        pedestrian_definition = {
            "x": 500,
            "y_offset": 45,
            "model": "girl",
            "label": None,
            "action": "still",
            "speed": 0,
        }
        car = EntityFactory.create_car(car_definition, road_y=300)
        pedestrian = EntityFactory.create_pedestrian(
            pedestrian_definition,
            road_y=300,
            rng=random.Random(1),
        )
        self.assertIsInstance(car, Car)
        self.assertEqual((130, 255, 60), (car.x, car.y, car.speed))
        self.assertIsInstance(pedestrian, Pedestrian)
        self.assertEqual(
            (500, 345, "girl"),
            (pedestrian.x, pedestrian.y, pedestrian.model),
        )

        definitions = {
            "Factory Test": {
                "cars": [car_definition],
                "pedestrians": [pedestrian_definition],
            }
        }
        direct = ScenarioFactory.create("Factory Test", 300, definitions)
        compatible = create_scenario("Factory Test", 300, definitions)
        self.assertEqual(direct.cars, compatible.cars)
        self.assertEqual(direct.pedestrians, compatible.pedestrians)


if __name__ == "__main__":
    unittest.main()
