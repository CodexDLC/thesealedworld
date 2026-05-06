from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.backend.core.exceptions import BusinessLogicException
from src.backend.features.character.events import CharacterEvents
from src.backend.features.items.events import ItemEvents
from src.backend.features.scenario.handlers.base_handler import ScenarioInitialHandlerContext
from src.backend.features.scenario.integrations.system_integrator import (
    SCENARIO_COMBAT_TTL_SECONDS,
    ScenarioSystemIntegrator,
)
from src.shared.enums import CoreDomain


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


@pytest.mark.unit
async def test_grant_inventory_rewards_creates_equipped_item_placements() -> None:
    events = MagicMock()
    events.request = AsyncMock(return_value={"status": "ok", "item_ids": ["item-1"], "items": None})
    integrator = ScenarioSystemIntegrator(
        sessions=MagicMock(),
        content=MagicMock(),
        character_sessions=MagicMock(),
        repo=MagicMock(),
        events=events,
    )

    item_ids = await integrator.grant_inventory_rewards(7, ["sword"], quest_key="awakening_rift")

    assert item_ids == ["item-1"]
    event_type, payload = events.request.await_args.args[:2]
    assert event_type == ItemEvents.GENERATE_REQUESTED
    assert payload["return_items"] is False
    assert payload["items"][0]["return_item"] is False
    assert payload["items"][0]["placement_ref"] == {
        "holder_type": "character",
        "holder_id": "7",
        "storage_type": "equipped",
        "slot": "main_hand",
        "position_index": None,
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
async def test_request_combat_start_uses_day_ttl() -> None:
    events = MagicMock()
    events.request = AsyncMock(return_value={"status": "ready", "combat_id": "combat-1"})
    integrator = ScenarioSystemIntegrator(
        sessions=MagicMock(),
        content=MagicMock(),
        character_sessions=MagicMock(),
        repo=MagicMock(),
        events=events,
    )

    await integrator.request_combat_start(7, "awakening_rift", battle_type="shadow", location_id="52_58")

    payload = events.request.await_args.args[1]
    assert payload["ttl"] == SCENARIO_COMBAT_TTL_SECONDS
