from unittest.mock import AsyncMock

import pytest

from src.backend.features.scenario.dto.context import ScenarioContextDTO
from src.backend.features.scenario.handlers.base_handler import ScenarioInitialHandlerContext
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
async def test_tutorial_finalize_requests_pve_combat_transition() -> None:
    integration = AsyncMock()
    integration.select_tutorial_pve_spawn_location.return_value = "52_45"
    handler = TutorialScenarioHandler(integration=integration)
    context = ScenarioContextDTO(quest_key="awakening_rift", current_node_key="final")

    result = await handler.on_finalize(1, context, {"quest_key": "awakening_rift"})

    integration.select_tutorial_pve_spawn_location.assert_awaited_once_with()
    assert result.target_state == CoreDomain.COMBAT
    assert result.transition_reason == "scenario_pve_combat"
    assert result.location_id == "52_45"
    assert result.metadata["battle_type"] == "pve"


@pytest.mark.unit
async def test_tutorial_initialize_uses_integration_context() -> None:
    integration = AsyncMock()
    integration.get_initial_handler_context.return_value = ScenarioInitialHandlerContext(
        sys_actor="Eidolon",
        prev_state="LOBBY",
        prev_loc="52_52",
    )
    handler = TutorialScenarioHandler(integration=integration)

    context = await handler.on_initialize(
        7,
        {"quest_key": "awakening_rift", "start_node_id": "start"},
    )

    integration.get_initial_handler_context.assert_awaited_once_with(7)
    assert context.sys_actor == "Eidolon"
    assert context.prev_state == "LOBBY"
    assert context.prev_loc == "52_52"
    integration.apply_initialize_effects.assert_not_awaited()


@pytest.mark.unit
async def test_tutorial_initialize_applies_npc_initialize_effects() -> None:
    integration = AsyncMock()
    integration.get_initial_handler_context.return_value = ScenarioInitialHandlerContext(
        sys_actor="Eidolon",
        prev_state="LOBBY",
        prev_loc="52_52",
    )
    handler = TutorialScenarioHandler(integration=integration)

    context = await handler.on_initialize(
        7,
        {"quest_key": "awakening_rift", "start_node_id": "start", "npc_key": "portal_pad_guide"},
    )

    assert context.npc_key == "portal_pad_guide"
    integration.apply_initialize_effects.assert_awaited_once()
