from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.backend.features.character.schemas.session import CharacterSessionDocumentDTO
from src.backend.features.game_session.integrations import GameSessionIntegrator
from src.backend.features.game_session.services.session_service import GameSessionService
from src.shared.enums import CoreDomain


class FakeGameSessionIntegrator:
    def __init__(self, *, session_doc=None):
        self.get_active_session = AsyncMock(return_value=session_doc)
        self.set_active_session_state = AsyncMock()
        self.reset_active_session_to_exploration = AsyncMock()
        self.respawn_character = AsyncMock(
            return_value={"status": "respawned", "location_id": "52_52", "corpse_id": "corpse-1"}
        )


def active_session(
    *,
    user_id=None,
    state=CoreDomain.EXPLORATION,
    prev_state=None,
    sessions=None,
    location=None,
) -> CharacterSessionDocumentDTO:
    return CharacterSessionDocumentDTO.model_validate(
        {
            "char_id": 7,
            "user_id": str(user_id or uuid4()),
            "state": state.value if isinstance(state, CoreDomain) else state,
            "prev_state": prev_state.value if isinstance(prev_state, CoreDomain) else prev_state,
            "bio": {
                "name": "Ada",
                "gender": "female",
                "created_at": "2026-05-05T00:00:00Z",
            },
            "location": location or {"current": "52_51", "prev": "52_52"},
            "sessions": sessions or {},
            "updated_at": "2026-05-05T00:00:00Z",
        }
    )


@pytest.mark.asyncio
async def test_enter_character_returns_lobby_transition_when_ac_is_missing():
    user_id = uuid4()
    integrator = FakeGameSessionIntegrator(session_doc=None)
    service = GameSessionService(integrator=integrator)

    response = await service.enter_character(SimpleNamespace(id=user_id), 7)

    assert response.header.current_state == CoreDomain.LOBBY
    assert response.payload_type == "state_transition"
    assert response.payload.target_state == CoreDomain.LOBBY
    integrator.get_active_session.assert_awaited_once_with(7, user_id)


@pytest.mark.asyncio
async def test_enter_character_routes_exploration_without_runtime_session_ref():
    user_id = uuid4()
    integrator = FakeGameSessionIntegrator(
        session_doc=active_session(user_id=user_id, state=CoreDomain.EXPLORATION, prev_state=CoreDomain.SCENARIO)
    )
    service = GameSessionService(integrator=integrator)

    response = await service.enter_character(SimpleNamespace(id=user_id), 7)

    assert response.header.current_state == CoreDomain.EXPLORATION
    assert response.header.previous_state == CoreDomain.SCENARIO
    assert response.payload_type == "exploration_session"
    assert response.payload["route_reason"] == "current_state"


@pytest.mark.asyncio
async def test_enter_character_routes_scenario_only_when_scenario_ref_exists():
    user_id = uuid4()
    integrator = FakeGameSessionIntegrator(
        session_doc=active_session(
            user_id=user_id,
            state=CoreDomain.SCENARIO,
            prev_state=CoreDomain.EXPLORATION,
            sessions={"scenario_id": "scenario-session-1"},
        )
    )
    service = GameSessionService(integrator=integrator)

    response = await service.enter_character(SimpleNamespace(id=user_id), 7)

    assert response.header.current_state == CoreDomain.SCENARIO
    assert response.payload_type == "scenario_session"
    assert response.payload["source"] == "hot_ac"
    integrator.reset_active_session_to_exploration.assert_not_awaited()


@pytest.mark.asyncio
async def test_enter_character_routes_combat_and_result_by_their_refs():
    user_id = uuid4()
    combat = active_session(
        user_id=user_id,
        state=CoreDomain.COMBAT,
        prev_state=CoreDomain.ARENA,
        sessions={"combat_id": "combat-1", "arena_id": "arena-1"},
    )
    result = active_session(
        user_id=user_id,
        state=CoreDomain.COMBAT_RESULT,
        prev_state=CoreDomain.ARENA,
        sessions={"combat_finalization_id": "combat-final-1", "arena_id": "arena-1"},
    )

    combat_response = await GameSessionService(
        integrator=FakeGameSessionIntegrator(session_doc=combat)
    ).enter_character(SimpleNamespace(id=user_id), 7)
    result_response = await GameSessionService(
        integrator=FakeGameSessionIntegrator(session_doc=result)
    ).enter_character(SimpleNamespace(id=user_id), 7)

    assert combat_response.header.current_state == CoreDomain.COMBAT
    assert combat_response.payload_type == "combats_session"
    assert result_response.header.current_state == CoreDomain.COMBAT_RESULT
    assert result_response.payload_type == "combat_result_session"


@pytest.mark.asyncio
async def test_enter_character_routes_arena_only_when_arena_ref_exists():
    user_id = uuid4()
    integrator = FakeGameSessionIntegrator(
        session_doc=active_session(
            user_id=user_id,
            state=CoreDomain.ARENA,
            prev_state=CoreDomain.EXPLORATION,
            sessions={"arena_id": "arena:runtime:1"},
        )
    )
    service = GameSessionService(integrator=integrator)

    response = await service.enter_character(SimpleNamespace(id=user_id), 7)

    assert response.header.current_state == CoreDomain.ARENA
    assert response.payload_type == "arena_session"


@pytest.mark.asyncio
async def test_enter_character_routes_combat_result_before_death_when_finalization_ref_exists():
    user_id = uuid4()
    integrator = FakeGameSessionIntegrator(
        session_doc=active_session(
            user_id=user_id,
            state=CoreDomain.DEATH,
            prev_state=CoreDomain.COMBAT_RESULT,
            sessions={"death_run_id": "run-1", "combat_finalization_id": "combat-final-1"},
        )
    )
    service = GameSessionService(integrator=integrator)

    response = await service.enter_character(SimpleNamespace(id=user_id), 7)

    assert response.header.current_state == CoreDomain.COMBAT_RESULT
    assert response.payload_type == "combat_result_session"
    assert response.payload["route_reason"] == "combat_result_pending"
    integrator.set_active_session_state.assert_awaited_once_with(7, CoreDomain.COMBAT_RESULT)


@pytest.mark.asyncio
async def test_enter_character_routes_death_when_death_ref_exists_without_pending_combat_result():
    user_id = uuid4()
    integrator = FakeGameSessionIntegrator(
        session_doc=active_session(
            user_id=user_id,
            state=CoreDomain.DEATH,
            prev_state=CoreDomain.COMBAT,
            sessions={"death_run_id": "run-1"},
        )
    )
    service = GameSessionService(integrator=integrator)

    response = await service.enter_character(SimpleNamespace(id=user_id), 7)

    assert response.header.current_state == CoreDomain.DEATH
    assert response.payload_type == "death_session"


@pytest.mark.asyncio
async def test_respawn_character_calls_integrator_from_death_state():
    user_id = uuid4()
    session_doc = active_session(
        user_id=user_id,
        state=CoreDomain.DEATH,
        prev_state=CoreDomain.COMBAT_RESULT,
        sessions={"death_run_id": "run-1"},
    )
    integrator = FakeGameSessionIntegrator(session_doc=session_doc)
    service = GameSessionService(integrator=integrator)

    response = await service.respawn_character(SimpleNamespace(id=user_id), 7)

    assert response.header.current_state == CoreDomain.EXPLORATION
    assert response.header.previous_state == CoreDomain.DEATH
    assert response.payload.target_state == CoreDomain.EXPLORATION
    assert response.payload.metadata["corpse_id"] == "corpse-1"
    integrator.respawn_character.assert_awaited_once_with(7)


@pytest.mark.asyncio
async def test_enter_character_uses_previous_valid_state_when_current_ref_is_missing():
    user_id = uuid4()
    integrator = FakeGameSessionIntegrator(
        session_doc=active_session(
            user_id=user_id,
            state=CoreDomain.COMBAT,
            prev_state=CoreDomain.SCENARIO,
            sessions={"scenario_id": "scenario-session-1"},
        )
    )
    service = GameSessionService(integrator=integrator)

    response = await service.enter_character(SimpleNamespace(id=user_id), 7)

    assert response.header.current_state == CoreDomain.SCENARIO
    assert response.payload["route_reason"] == "previous_state_fallback"
    integrator.set_active_session_state.assert_awaited_once_with(7, CoreDomain.SCENARIO)


@pytest.mark.asyncio
async def test_enter_character_resets_to_exploration_when_current_and_previous_are_invalid():
    user_id = uuid4()
    integrator = FakeGameSessionIntegrator(
        session_doc=active_session(
            user_id=user_id,
            state=CoreDomain.ARENA,
            prev_state=CoreDomain.SCENARIO,
            sessions={},
        )
    )
    service = GameSessionService(integrator=integrator)

    response = await service.enter_character(SimpleNamespace(id=user_id), 7)

    assert response.header.current_state == CoreDomain.EXPLORATION
    assert response.payload["route_reason"] == "reset_to_exploration"
    integrator.reset_active_session_to_exploration.assert_awaited_once_with(7)


@pytest.mark.asyncio
async def test_integrator_sets_active_session_state():
    sessions = SimpleNamespace(patch_fields=AsyncMock(), mark_dirty=AsyncMock())
    integrator = GameSessionIntegrator(character_sessions=sessions)

    await integrator.set_active_session_state(7, CoreDomain.ARENA)

    sessions.patch_fields.assert_awaited_once_with(7, {"$.state": CoreDomain.ARENA.value})
    sessions.mark_dirty.assert_awaited_once_with(
        7,
        reason="game_session_state_fallback",
        paths=["$.state"],
    )


@pytest.mark.asyncio
async def test_integrator_resets_active_session_to_exploration():
    sessions = SimpleNamespace(reset_main_runtime_refs_to_exploration=AsyncMock())
    integrator = GameSessionIntegrator(character_sessions=sessions)

    await integrator.reset_active_session_to_exploration(7)

    sessions.reset_main_runtime_refs_to_exploration.assert_awaited_once_with(7)
