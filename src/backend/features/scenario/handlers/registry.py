from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.scenario.handlers.dialogue_handler import DialogueScenarioHandler
from src.backend.features.scenario.handlers.tutorial_handler import TutorialScenarioHandler

if TYPE_CHECKING:
    from src.backend.features.scenario.handlers.base_handler import BaseScenarioHandler, ScenarioHandlerIntegration

_UNIQUE_HANDLERS: dict[str, type[BaseScenarioHandler]] = {
    "awakening_rift": TutorialScenarioHandler,
}
_SCENARIO_TYPE_HANDLERS: dict[str, type[BaseScenarioHandler]] = {
    "dialogue_scenario": DialogueScenarioHandler,
}


def get_handler(
    quest_key: str,
    *,
    scenario_type: str,
    integration: ScenarioHandlerIntegration,
) -> BaseScenarioHandler:
    if scenario_type == "unique_scenario":
        handler_class = _UNIQUE_HANDLERS.get(quest_key)
        if handler_class is None:
            raise KeyError(f"Unique scenario handler not found: {quest_key}")
        return handler_class(integration)

    handler_class = _SCENARIO_TYPE_HANDLERS.get(scenario_type)
    if handler_class is None:
        raise KeyError(f"Scenario handler not found: quest_key={quest_key} scenario_type={scenario_type}")
    return handler_class(integration)
