import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.backend.core.exceptions import BusinessLogicException
from src.backend.features.character.events import CharacterEvents
from src.backend.features.inventory.events.publisher import InventoryEvents
from src.backend.features.items.events.publisher import ItemEvents
from src.backend.features.scenario.dto.context import ScenarioContextDTO
from src.backend.features.scenario.handlers.base_handler import ScenarioInitialHandlerContext
from src.backend.features.scenario.integrations.system_integrator import (
    MONSTER_GROUP_PREPARE_REQUESTED,
    SCENARIO_COMBAT_TTL_SECONDS,
    TUTORIAL_PVE_CROSS_ZONE_IDS,
    ScenarioSystemIntegrator,
    _budget_from_gear_score,
)
from src.shared.enums import CoreDomain
from src.shared.schemas import ScenarioReturnContextDTO


@pytest.mark.unit
async def test_unlock_skills_updates_active_character_runtime() -> None:
    events = MagicMock()
    events.request = AsyncMock(return_value={"status": "ok", "skill_keys": ["skill_swords"]})
    integrator = ScenarioSystemIntegrator(
        sessions=MagicMock(),
        content=MagicMock(),
        character_sessions=MagicMock(),
        repo=MagicMock(),
        events=events,
    )

    await integrator.unlock_skills(7, ["skill_swords"])

    events.request.assert_awaited_once()
    event_type, payload = events.request.await_args.args[:2]
    assert event_type == CharacterEvents.SKILLS_UNLOCK_REQUESTED
    assert payload["char_id"] == 7
    assert payload["skill_keys"] == '["skill_swords"]'
    assert "initial_xp" not in payload


@pytest.mark.unit
async def test_unlock_skills_can_pass_initial_xp_to_character_runtime() -> None:
    events = MagicMock()
    events.request = AsyncMock(return_value={"status": "ok", "skill_keys": ["skill_swords"]})
    integrator = ScenarioSystemIntegrator(
        sessions=MagicMock(),
        content=MagicMock(),
        character_sessions=MagicMock(),
        repo=MagicMock(),
        events=events,
    )

    await integrator.unlock_skills(7, ["skill_swords"], initial_xp=0.10)

    payload = events.request.await_args.args[1]
    assert payload["initial_xp"] == 0.10


@pytest.mark.unit
async def test_grant_inventory_rewards_requests_inventory_reward_grant() -> None:
    events = MagicMock()
    events.request = AsyncMock(
        side_effect=[
            {"status": "ok", "item_ids": ["item-1"]},
            {
                "status": "ok",
                "item_ids": ["item-1"],
                "equipped_item_ids": ["item-1"],
                "backpack_item_ids": [],
            },
        ]
    )
    integrator = ScenarioSystemIntegrator(
        sessions=MagicMock(),
        content=MagicMock(),
        character_sessions=MagicMock(),
        repo=MagicMock(),
        events=events,
    )

    item_ids = await integrator.grant_inventory_rewards(7, ["sword"], quest_key="awakening_rift")

    assert item_ids == ["item-1"]
    first_call, second_call = events.request.await_args_list
    event_type, payload = first_call.args[:2]
    assert event_type == ItemEvents.GENERATE_REQUESTED
    assert payload["items"][0]["base_id"] == "sword"
    assert payload["items"][0]["placement_ref"]["storage_type"] == "backpack"
    assert payload["items"][0]["origin_ref"]["origin_ref"] == "awakening_rift"

    event_type, payload = second_call.args[:2]
    assert event_type == InventoryEvents.REWARDS_GRANT_REQUESTED
    assert payload == {
        "char_id": 7,
        "quest_key": "awakening_rift",
        "item_ids": ["item-1"],
        "equip_if_possible": True,
    }


@pytest.mark.unit
async def test_ensure_character_owner_rejects_missing_character() -> None:
    character_repo = MagicMock()
    character_repo.get_by_id_and_user_id = AsyncMock(return_value=None)
    integrator = ScenarioSystemIntegrator(
        sessions=MagicMock(),
        content=MagicMock(),
        character_sessions=MagicMock(),
        repo=MagicMock(),
        events=MagicMock(),
        character_repo=character_repo,
    )

    with pytest.raises(BusinessLogicException):
        await integrator.ensure_character_owner(user_id=uuid4(), char_id=7)


@pytest.mark.unit
async def test_get_initial_handler_context_reads_character_session_sections() -> None:
    character_sessions = MagicMock()
    character_sessions.get_section = AsyncMock(
        side_effect=[
            {"name": "Eidolon"},
            {"current": "52_52"},
            "LOBBY",
        ],
    )
    integrator = ScenarioSystemIntegrator(
        sessions=MagicMock(),
        content=MagicMock(),
        character_sessions=character_sessions,
        repo=MagicMock(),
        events=MagicMock(),
    )

    context = await integrator.get_initial_handler_context(7)

    assert context == ScenarioInitialHandlerContext(
        sys_actor="Eidolon",
        prev_state="LOBBY",
        prev_loc="52_52",
    )


@pytest.mark.unit
async def test_recover_missing_finish_to_exploration_clears_stale_scenario_state() -> None:
    character_sessions = MagicMock()
    character_sessions.get_section = AsyncMock(return_value=CoreDomain.SCENARIO.value)
    character_sessions.set_state = AsyncMock()
    character_sessions.clear_scenario_session = AsyncMock()
    sessions = MagicMock()
    sessions.delete = AsyncMock()
    repo = MagicMock()
    repo.delete_state = AsyncMock()
    integrator = ScenarioSystemIntegrator(
        sessions=sessions,
        content=MagicMock(),
        character_sessions=character_sessions,
        repo=repo,
        events=MagicMock(),
    )

    await integrator.recover_missing_finish_to_exploration(7)

    character_sessions.set_state.assert_awaited_once_with(
        7,
        CoreDomain.EXPLORATION,
        prev_state=CoreDomain.SCENARIO,
    )
    character_sessions.clear_scenario_session.assert_awaited_once_with(7)
    sessions.delete.assert_awaited_once_with(7)
    repo.delete_state.assert_awaited_once_with(7)


@pytest.mark.unit
async def test_finalize_session_can_persist_exploration_as_previous_state() -> None:
    character_sessions = MagicMock()
    character_sessions.transition_state = AsyncMock()
    character_sessions.clear_scenario_session = AsyncMock()
    sessions = MagicMock()
    sessions.delete = AsyncMock()
    repo = MagicMock()
    repo.delete_state = AsyncMock()
    integrator = ScenarioSystemIntegrator(
        sessions=sessions,
        content=MagicMock(),
        character_sessions=character_sessions,
        repo=repo,
        events=MagicMock(),
    )

    await integrator.finalize_session(7, CoreDomain.EXPLORATION, prev_state=CoreDomain.EXPLORATION)

    character_sessions.transition_state.assert_awaited_once_with(
        7,
        CoreDomain.EXPLORATION,
        expected_state=CoreDomain.SCENARIO,
        prev_state=CoreDomain.EXPLORATION,
    )
    character_sessions.clear_scenario_session.assert_awaited_once_with(7)
    sessions.delete.assert_awaited_once_with(7)
    repo.delete_state.assert_awaited_once_with(7)


@pytest.mark.unit
async def test_prepare_session_uses_return_context_source_state() -> None:
    sessions = MagicMock()
    sessions.create = AsyncMock()
    character_sessions = MagicMock()
    character_sessions.transition_state = AsyncMock()
    character_sessions.set_scenario_session = AsyncMock()
    repo = MagicMock()
    repo.upsert_state = AsyncMock()
    integrator = ScenarioSystemIntegrator(
        sessions=sessions,
        content=MagicMock(),
        character_sessions=character_sessions,
        repo=repo,
        events=MagicMock(),
    )
    context = ScenarioContextDTO(
        quest_key="tavern_bartender_dialogue",
        current_node_key="start",
        return_context=ScenarioReturnContextDTO(
            source_state=CoreDomain.CITY_SERVICES,
            return_state=CoreDomain.CITY_SERVICES,
            return_screen="bar",
            source_service_id="svc_tavern_hub",
            location_id="52_53",
            tavern_id="last_refuge",
        ),
    )

    await integrator.prepare_session(7, "tavern_bartender_dialogue", context)

    character_sessions.transition_state.assert_awaited_once_with(
        7,
        CoreDomain.SCENARIO,
        expected_state=CoreDomain.CITY_SERVICES.value,
        prev_state=CoreDomain.CITY_SERVICES.value,
    )
    sessions.create.assert_awaited_once_with(7, context)
    character_sessions.set_scenario_session.assert_awaited_once()
    repo.upsert_state.assert_awaited_once()


@pytest.mark.unit
async def test_prepare_session_cleans_scenario_session_when_transition_fails() -> None:
    sessions = MagicMock()
    sessions.create = AsyncMock()
    sessions.delete = AsyncMock()
    character_sessions = MagicMock()
    character_sessions.transition_state = AsyncMock(side_effect=RuntimeError("bad state"))
    integrator = ScenarioSystemIntegrator(
        sessions=sessions,
        content=MagicMock(),
        character_sessions=character_sessions,
        repo=MagicMock(),
        events=MagicMock(),
    )
    context = ScenarioContextDTO(quest_key="q1", current_node_key="start", prev_state=CoreDomain.LOBBY.value)

    with pytest.raises(RuntimeError, match="bad state"):
        await integrator.prepare_session(7, "q1", context)

    sessions.create.assert_awaited_once_with(7, context)
    sessions.delete.assert_awaited_once_with(7)


@pytest.mark.unit
async def test_apply_finalize_effects_grants_tavern_room() -> None:
    events = MagicMock()
    events.request = AsyncMock(
        return_value={
            "status": "ok",
            "room_id": 10,
            "room_key": "last_refuge_private_room",
            "tavern_id": "last_refuge",
            "created": False,
        }
    )
    integrator = ScenarioSystemIntegrator(
        sessions=MagicMock(),
        content=MagicMock(),
        character_sessions=MagicMock(),
        repo=MagicMock(),
        events=events,
    )
    metadata = {
        "_effects": [
            {
                "type": "tavern.grant_room",
                "required": True,
                "tavern_id": "last_refuge",
                "room_key": "last_refuge_private_room",
            }
        ]
    }

    result = await integrator.apply_finalize_effects(7, metadata, quest_key="tavern_bartender_dialogue")

    assert metadata == {}
    assert result["room_granted"] is True
    assert result["room_id"] == 10
    assert result["room_created"] is False
    events.request.assert_awaited_once()
    assert events.request.await_args.args[0] == "tavern.room_grant_requested"


@pytest.mark.unit
async def test_apply_finalize_effects_fails_required_tavern_effect() -> None:
    events = MagicMock()
    events.request = AsyncMock(return_value={"status": "error", "error": "db down"})
    integrator = ScenarioSystemIntegrator(
        sessions=MagicMock(),
        content=MagicMock(),
        character_sessions=MagicMock(),
        repo=MagicMock(),
        events=events,
    )

    with pytest.raises(RuntimeError, match="City service tavern room grant effect failed"):
        await integrator.apply_finalize_effects(
            7,
            {"_effects": [{"type": "tavern.grant_room", "required": True, "tavern_id": "last_refuge"}]},
            quest_key="tavern_bartender_dialogue",
        )


@pytest.mark.unit
async def test_enter_prepared_combat_attaches_combat_and_switches_state() -> None:
    character_sessions = MagicMock()
    character_sessions.set_combat_session = AsyncMock()
    character_sessions.set_state = AsyncMock()
    integrator = ScenarioSystemIntegrator(
        sessions=MagicMock(),
        content=MagicMock(),
        character_sessions=character_sessions,
        repo=MagicMock(),
        events=MagicMock(),
    )

    await integrator.enter_prepared_combat(7, "combat-1")

    character_sessions.set_combat_session.assert_awaited_once_with(7, "combat-1")
    character_sessions.set_state.assert_awaited_once_with(
        7,
        CoreDomain.COMBAT,
        prev_state=CoreDomain.EXPLORATION,
    )


@pytest.mark.unit
async def test_select_tutorial_pve_spawn_location_uses_cross_zone_passable_non_safe_nodes() -> None:
    world_data = MagicMock()
    world_data.get_active_nodes_by_zone_ids = AsyncMock(
        return_value=[
            SimpleNamespace(x=46, y=46, zone_id="D4_0_0", is_active=True, flags={"is_passable": True}),
            SimpleNamespace(x=52, y=52, zone_id="D4_1_1", is_active=True, flags={"is_safe_zone": True}),
            SimpleNamespace(x=52, y=45, zone_id="D4_1_0", is_active=True, flags={"is_passable": False}),
            SimpleNamespace(x=55, y=52, zone_id="D4_2_1", is_active=False, flags={"is_passable": True}),
            SimpleNamespace(x=45, y=52, zone_id="D4_0_1", is_active=True, flags={"is_passable": True}),
        ]
    )
    integrator = ScenarioSystemIntegrator(
        sessions=MagicMock(),
        content=MagicMock(),
        character_sessions=MagicMock(),
        repo=MagicMock(),
        events=MagicMock(),
        world_data=world_data,
    )

    loc_id = await integrator.select_tutorial_pve_spawn_location()

    assert loc_id == "45_52"
    world_data.get_active_nodes_by_zone_ids.assert_awaited_once_with(list(TUTORIAL_PVE_CROSS_ZONE_IDS))


@pytest.mark.unit
def test_tutorial_pve_budget_uses_round_half_up_with_minimum() -> None:
    assert _budget_from_gear_score(13) == 3
    assert _budget_from_gear_score(12.5) == 3
    assert _budget_from_gear_score(2) == 1
    assert _budget_from_gear_score(0) == 1


@pytest.mark.unit
async def test_request_combat_start_prepares_monster_group_and_pve_combat() -> None:
    events = MagicMock()
    events.request = AsyncMock(
        side_effect=[
            {"status": "ok", "vitals": {"hp": {"cur": 64, "max": 64}}},
            {
                "status": "ok",
                "payload": {
                    "group_id": "combat-1",
                    "clan_id": "clan-1",
                    "family_id": "wolf_pack",
                    "monster_ids": ["m1", "m2"],
                    "actor_commitments": {
                        "monster:m1": "snapshot-m1",
                        "monster:m2": "snapshot-m2",
                    },
                },
            },
            {"status": "ok", "commitments": {"player:7": "snapshot-1"}},
            {"status": "ready", "combat_id": "combat-1", "battle_type": "pve"},
        ]
    )
    character_sessions = MagicMock()
    character_sessions.get_section = AsyncMock(return_value={"gear_score": 13})
    integrator = ScenarioSystemIntegrator(
        sessions=MagicMock(),
        content=MagicMock(),
        character_sessions=character_sessions,
        repo=MagicMock(),
        events=events,
    )

    result = await integrator.request_combat_start(7, "awakening_rift", battle_type="pve", location_id="45_52")

    restore_event, monster_event, commitment_event, combat_event = events.request.await_args_list
    assert restore_event.args[0] == CharacterEvents.VITALS_RESTORE_REQUESTED
    assert restore_event.args[1]["char_id"] == 7
    assert monster_event.args[0] == MONSTER_GROUP_PREPARE_REQUESTED
    assert monster_event.args[1]["loc_id"] == "45_52"
    assert monster_event.args[1]["budget"] == "3"
    assert monster_event.args[1]["ttl"] == SCENARIO_COMBAT_TTL_SECONDS
    assert commitment_event.args[0] == CharacterEvents.COMBAT_COMMITMENTS_REQUESTED
    payload = combat_event.args[1]
    assert payload["ttl"] == SCENARIO_COMBAT_TTL_SECONDS
    assert payload["battle_type"] == "pve"
    assert json.loads(payload["participants"]) == {"team_1": [7], "team_2": ["m1", "m2"]}
    assert json.loads(payload["commitments"]) == {
        "player:7": "snapshot-1",
        "monster:m1": "snapshot-m1",
        "monster:m2": "snapshot-m2",
    }
    assert payload["location_id"] == "45_52"
    assert result["monster_group"]["monster_ids"] == ["m1", "m2"]
