import pytest

from src.backend.features.scenario.handlers.dialogue_handler import DialogueScenarioHandler
from src.backend.features.scenario.handlers.registry import get_handler
from src.backend.features.scenario.handlers.tutorial_handler import TutorialScenarioHandler


@pytest.mark.unit
def test_handler_registry_uses_unique_override_for_awakening_rift() -> None:
    handler = get_handler(
        "awakening_rift",
        scenario_type="unique_scenario",
        integration=object(),
    )

    assert isinstance(handler, TutorialScenarioHandler)


@pytest.mark.unit
def test_handler_registry_uses_dialogue_handler_by_scenario_type() -> None:
    handler = get_handler(
        "tavern_bartender_dialogue",
        scenario_type="dialogue_scenario",
        integration=object(),
    )

    assert isinstance(handler, DialogueScenarioHandler)


@pytest.mark.unit
def test_handler_registry_does_not_fallback_for_unknown_unique_quest() -> None:
    with pytest.raises(KeyError, match="Unique scenario handler not found"):
        get_handler("unknown_unique", scenario_type="unique_scenario", integration=object())
