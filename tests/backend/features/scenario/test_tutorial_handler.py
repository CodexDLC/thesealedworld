import pytest

from src.backend.features.scenario.dto.context import ScenarioContextDTO
from src.backend.features.scenario.handlers.tutorial_handler import TutorialScenarioHandler
from src.shared.enums import CoreDomain


def test_tutorial_attribute_bonuses_rank_visible_profile_weights() -> None:
    context = ScenarioContextDTO(quest_key="awakening_rift", current_node_key="final")
    context.weights.stats.update(
        {
            "agility": 10,
            "projection": 1,
            "endurance": 10,
            "intellect": 5,
            "prediction": 7,
            "mental": 7,
            "perception": 9,
            "strength": 11,
            "memory": 5,
        }
    )

    assert TutorialScenarioHandler._calculate_attribute_bonuses(context) == {
        "strength": 9,
        "agility": 8,
        "endurance": 7,
        "perception": 6,
        "prediction": 5,
        "mental": 4,
        "intellect": 3,
        "memory": 2,
        "projection": 1,
    }


@pytest.mark.unit
async def test_tutorial_finalize_requests_shadow_combat_transition() -> None:
    handler = TutorialScenarioHandler(character_sessions=None)
    context = ScenarioContextDTO(quest_key="awakening_rift", current_node_key="final")

    result = await handler.on_finalize(1, context, {"quest_key": "awakening_rift"})

    assert result.target_state == CoreDomain.COMBAT
    assert result.transition_reason == "scenario_shadow_combat"
    assert result.location_id
    assert result.metadata["battle_type"] == "shadow"
