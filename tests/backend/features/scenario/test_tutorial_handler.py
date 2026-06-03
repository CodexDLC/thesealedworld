from unittest.mock import AsyncMock

import pytest

from src.backend.features.scenario.dto.context import ScenarioContextDTO
from src.backend.features.scenario.handlers.base_handler import ScenarioInitialHandlerContext
from src.backend.features.scenario.handlers.tutorial_handler import TutorialScenarioHandler
from src.shared.enums import CoreDomain


@pytest.mark.unit
async def test_tutorial_finalize_requests_outskirts_exploration_handoff() -> None:
    integration = AsyncMock()
    integration.select_tutorial_outskirts_spawn_location.return_value = "52_45"
    handler = TutorialScenarioHandler(integration=integration)
    context = ScenarioContextDTO(quest_key="awakening_rift", current_node_key="final")

    result = await handler.on_finalize(1, context, {"quest_key": "awakening_rift"})

    integration.select_tutorial_outskirts_spawn_location.assert_awaited_once_with()
    assert result.target_state == CoreDomain.EXPLORATION
    assert result.transition_reason == "scenario_outskirts_handoff"
    assert result.location_id == "52_45"
    assert result.metadata == {"quest_key": "awakening_rift"}
    assert result.rewards.items == []
    assert result.rewards.skills == []
    assert result.rewards.attribute_bonuses == {}


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


@pytest.mark.unit
async def test_tutorial_initialize_routes_to_death_respawn_arrival_when_attempt_gt_1() -> None:
    from src.shared.schemas.scenario import ScenarioReturnContextDTO
    from src.shared.enums import CoreDomain

    integration = AsyncMock()
    integration.get_initial_handler_context.return_value = ScenarioInitialHandlerContext(
        sys_actor="Eidolon",
        prev_state="LOBBY",
        prev_loc="52_52",
    )
    handler = TutorialScenarioHandler(integration=integration)

    return_context = ScenarioReturnContextDTO(
        source_state=CoreDomain.EXPLORATION,
        return_state=CoreDomain.SCENARIO,
        metadata={"attempt_index": 2},
    )

    context = await handler.on_initialize(
        7,
        {"quest_key": "awakening_rift", "start_node_id": "start"},
        return_context=return_context,
    )

    assert context.current_node_key == "death_respawn_arrival"
    assert context.flags.get("attempt_index") == 2
