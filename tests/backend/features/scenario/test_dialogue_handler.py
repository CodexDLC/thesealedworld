from unittest.mock import AsyncMock

import pytest

from src.backend.features.scenario.handlers.base_handler import ScenarioInitialHandlerContext
from src.backend.features.scenario.handlers.dialogue_handler import DialogueScenarioHandler
from src.shared.enums import CoreDomain
from src.shared.schemas import ScenarioReturnContextDTO


@pytest.mark.unit
async def test_dialogue_handler_initializes_from_return_context() -> None:
    integration = AsyncMock()
    integration.get_initial_handler_context.return_value = ScenarioInitialHandlerContext(
        sys_actor="Mote",
        prev_state=CoreDomain.EXPLORATION.value,
        prev_loc="52_52",
    )
    handler = DialogueScenarioHandler(integration=integration)
    return_context = ScenarioReturnContextDTO(
        source_state=CoreDomain.CITY_SERVICES,
        return_state=CoreDomain.CITY_SERVICES,
        return_screen="bar",
        source_service_id="svc_tavern_hub",
        location_id="53_53",
        tavern_id="last_refuge",
    )

    context = await handler.on_initialize(
        7,
        {
            "quest_key": "tavern_bartender_dialogue",
            "scenario_type": "dialogue_scenario",
            "start_node_id": "bartender_greeting",
        },
        return_context=return_context,
    )

    assert context.quest_key == "tavern_bartender_dialogue"
    assert context.current_node_key == "bartender_greeting"
    assert context.prev_state == CoreDomain.CITY_SERVICES.value
    assert context.prev_loc == "53_53"
    assert context.return_context == return_context
    assert context.npc_key is None


@pytest.mark.unit
async def test_dialogue_handler_resolves_npc_key_from_master() -> None:
    integration = AsyncMock()
    integration.get_initial_handler_context.return_value = ScenarioInitialHandlerContext(
        sys_actor="Mote",
        prev_state=CoreDomain.EXPLORATION.value,
        prev_loc="52_52",
    )
    handler = DialogueScenarioHandler(integration=integration)

    context = await handler.on_initialize(
        7,
        {
            "quest_key": "first_death_portal_dialogue",
            "scenario_type": "dialogue_scenario",
            "start_node_id": "first_contact",
            "npc_key": "portal_pad_guide",
        },
    )

    assert context.npc_key == "portal_pad_guide"


@pytest.mark.unit
async def test_dialogue_handler_finalizes_with_structured_metadata() -> None:
    integration = AsyncMock()
    integration.get_initial_handler_context.return_value = ScenarioInitialHandlerContext(
        sys_actor="Mote",
        prev_state=CoreDomain.CITY_SERVICES.value,
        prev_loc="53_53",
    )
    integration.get_node.return_value = {
        "node_key": "final_room",
        "metadata": {
            "finalize": {
                "target_state": "city_services",
                "transition_reason": "tavern_bartender_room_granted",
                "next_screen": "room",
                "response_metadata": {"room_granted": True, "bartender_rep_delta": 1},
                "effects": [
                    {
                        "type": "tavern.grant_room",
                        "required": True,
                        "tavern_id": "last_refuge",
                        "room_key": "last_refuge_private_room",
                    }
                ],
            }
        },
    }
    handler = DialogueScenarioHandler(integration=integration)
    return_context = ScenarioReturnContextDTO(
        source_state=CoreDomain.CITY_SERVICES,
        return_state=CoreDomain.CITY_SERVICES,
        return_screen="bar",
        source_service_id="svc_tavern_hub",
        location_id="53_53",
        tavern_id="last_refuge",
    )
    context = await handler.on_initialize(
        7,
        {
            "quest_key": "tavern_bartender_dialogue",
            "scenario_type": "dialogue_scenario",
            "start_node_id": "final_room",
        },
        return_context=return_context,
    )

    result = await handler.on_finalize(7, context, {"quest_key": "tavern_bartender_dialogue"})

    assert result.target_state == CoreDomain.CITY_SERVICES
    assert result.transition_reason == "tavern_bartender_room_granted"
    assert result.location_id == "53_53"
    assert result.metadata["next_screen"] == "room"
    assert result.metadata["room_granted"] is True
    assert result.metadata["return_context"]["tavern_id"] == "last_refuge"
    assert result.metadata["_effects"][0]["type"] == "tavern.grant_room"
