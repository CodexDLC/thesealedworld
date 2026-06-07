from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.backend.features.character.schemas.session import CharacterSessionDocumentDTO
from src.backend.features.game_session.integrations import GameSessionIntegrator
from src.backend.features.game_session.services.session_service import GameSessionService
from src.shared.enums import CoreDomain
from src.shared.schemas.loot import ClaimResultDTO


class FakeGameSessionIntegrator:
    def __init__(self, *, session_doc=None):
        self.get_active_session = AsyncMock(return_value=session_doc)
        self.set_active_session_state = AsyncMock()
        self.reset_active_session_to_exploration = AsyncMock()
        self.respawn_character = AsyncMock(
            return_value={"status": "respawned", "location_id": "52_52", "corpse_id": "corpse-1"}
        )
        self.resolve_starter_rift_death_context = AsyncMock(return_value=None)
        self.reset_starter_rift_character = AsyncMock()
        self.claim_post_combat_loot = AsyncMock(return_value={"status": "loot_claim_queued", "target_state": "rift"})


class FakeLootService:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    async def claim_all(self, _character_id: int, _corpse_ids: list[str]) -> ClaimResultDTO:
        suffix = str(_corpse_ids[0]).rsplit("-", maxsplit=1)[-1] if _corpse_ids else "1"
        return ClaimResultDTO(
            instance_ids=[f"item-{suffix}"],
            resource_deltas={"coin_copper": 3},
            summary_items=["Медные монеты x3", "Ржавый клинок"],
        )


class FakeArq:
    def __init__(self) -> None:
        self.jobs: list[tuple[str, dict]] = []

    async def enqueue_job(self, name: str, payload: dict) -> None:
        self.jobs.append((name, payload))


class FakeCharacterSessions:
    def __init__(self, document: dict | None = None) -> None:
        self.document = document or {}
        self.patches: list[tuple[int, dict]] = []
        self.dirty: list[tuple[int, str, list[str]]] = []

    async def get_session(self, char_id: int) -> dict:
        assert char_id == 7
        return self.document

    async def patch_fields(self, char_id: int, fields: dict) -> None:
        self.patches.append((char_id, fields))

    async def mark_dirty(self, char_id: int, *, reason: str, paths: list[str]) -> None:
        self.dirty.append((char_id, reason, paths))


class FakeRiftRuntimeForDeath:
    def __init__(self, *, setting_key: str = "starter_rift") -> None:
        self.setting_key = setting_key

    async def require_run_session(self, rift_session_id: str) -> dict:
        assert rift_session_id == "rift-run-1"
        return {
            "rift_session_id": "rift-run-1",
            "rift_instance_id": "rift-instance-1",
            "current_node_id": "z01:2_2",
            "active_encounter_id": "combat-1",
        }

    async def require_instance(self, rift_instance_id: str) -> SimpleNamespace:
        assert rift_instance_id == "rift-instance-1"
        return SimpleNamespace(
            rift_instance_id=rift_instance_id,
            setting={"setting_key": self.setting_key},
            population_context={"setting_key": self.setting_key},
        )


class FakeRiftRuntime:
    def __init__(self) -> None:
        self.cleared: list[str] = []
        self.applied: list[dict] = []

    async def clear_run_active_encounter(self, rift_session_id: str) -> None:
        self.cleared.append(rift_session_id)

    async def apply_combat_result(self, **kwargs) -> dict:
        self.applied.append(kwargs)
        return {"applied": True}


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
async def test_enter_character_routes_rift_only_when_rift_ref_exists():
    user_id = uuid4()
    integrator = FakeGameSessionIntegrator(
        session_doc=active_session(
            user_id=user_id,
            state=CoreDomain.RIFT,
            prev_state=CoreDomain.SCENARIO,
            sessions={"rift_session_id": "rift-run-1", "rift_instance_id": "rift-instance-1"},
        )
    )
    service = GameSessionService(integrator=integrator)

    response = await service.enter_character(SimpleNamespace(id=user_id), 7)

    assert response.header.current_state == CoreDomain.RIFT
    assert response.header.previous_state == CoreDomain.SCENARIO
    assert response.payload_type == "rift_session"
    assert response.payload["route_reason"] == "current_state"
    integrator.reset_active_session_to_exploration.assert_not_awaited()


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
async def test_enter_character_routes_loot_when_post_combat_ref_exists():
    user_id = uuid4()
    integrator = FakeGameSessionIntegrator(
        session_doc=active_session(
            user_id=user_id,
            state=CoreDomain.LOOT,
            prev_state=CoreDomain.COMBAT_RESULT,
            sessions={"post_combat": {"target_state": "loot", "corpse_ids": ["corpse-1"]}},
        )
    )
    service = GameSessionService(integrator=integrator)

    response = await service.enter_character(SimpleNamespace(id=user_id), 7)

    assert response.header.current_state == CoreDomain.LOOT
    assert response.payload_type == "loot_session"


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
async def test_respawn_character_returns_to_awakening_rift_after_starter_rift_death():
    user_id = uuid4()
    session_doc = active_session(
        user_id=user_id,
        state=CoreDomain.DEATH,
        prev_state=CoreDomain.COMBAT_RESULT,
        sessions={
            "death_run_id": "run-1",
            "rift_session_id": "rift-run-1",
            "rift_instance_id": "rift-instance-1",
        },
    )
    starter_context = {
        "rift_key": "starter_rift",
        "rift_session_id": "rift-run-1",
        "rift_instance_id": "rift-instance-1",
        "current_node_id": "z01:2_2",
        "active_encounter_id": "combat-1",
    }
    integrator = FakeGameSessionIntegrator(session_doc=session_doc)
    integrator.resolve_starter_rift_death_context.return_value = starter_context
    integrator.reset_starter_rift_character.return_value = {
        "status": "reset",
        "attempt_index": 1,
        "starting_imprint": {
            "imprint_key": "starter_guard_01",
            "attributes": {"endurance": 17, "strength": 16},
            "item_ids": ["item-1"],
        },
    }
    npc = SimpleNamespace(get_or_create_state=AsyncMock(return_value=SimpleNamespace(flags={})))
    service = GameSessionService(integrator=integrator).bind_npc(npc)

    response = await service.respawn_character(SimpleNamespace(id=user_id), 7)

    assert response.header.current_state == CoreDomain.SCENARIO
    assert response.header.previous_state == CoreDomain.DEATH
    assert response.payload.target_state == CoreDomain.SCENARIO
    assert response.payload.reason == "starter_rift_reset"
    assert response.payload.quest_key == "awakening_rift"
    assert response.payload.location_id == "52_52"
    assert response.payload.metadata["attempt_index"] == 1
    assert response.payload.metadata["starting_imprint"]["imprint_key"] == "starter_guard_01"
    assert response.payload.metadata["starting_imprint"]["attributes"]["endurance"] == 17
    assert response.payload.context["return_context"]["source_state"] == CoreDomain.EXPLORATION.value
    assert response.payload.context["return_context"]["return_state"] == CoreDomain.SCENARIO.value
    assert response.payload.context["return_context"]["metadata"]["original_source_state"] == CoreDomain.RIFT.value
    assert response.payload.context["return_context"]["metadata"]["initial_node_key"] == "rift_entry_01"
    assert response.payload.context["return_context"]["metadata"]["rift_session_id"] == "rift-run-1"
    assert response.payload.context["return_context"]["metadata"]["rift_instance_id"] == "rift-instance-1"
    integrator.resolve_starter_rift_death_context.assert_awaited_once_with(session_doc)
    integrator.reset_starter_rift_character.assert_awaited_once_with(
        7,
        user_id=user_id,
        starter_context=starter_context,
        respawn_result={"status": "respawned", "location_id": "52_52", "corpse_id": "corpse-1"},
    )
    npc.get_or_create_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_respawn_character_starts_first_death_dialogue_on_portal_pad():
    user_id = uuid4()
    session_doc = active_session(
        user_id=user_id,
        state=CoreDomain.DEATH,
        prev_state=CoreDomain.COMBAT_RESULT,
        sessions={"death_run_id": "run-1"},
    )
    integrator = FakeGameSessionIntegrator(session_doc=session_doc)
    npc = SimpleNamespace(
        get_or_create_state=AsyncMock(return_value=SimpleNamespace(flags={})),
    )
    service = GameSessionService(integrator=integrator).bind_npc(npc)

    response = await service.respawn_character(SimpleNamespace(id=user_id), 7)

    assert response.header.current_state == CoreDomain.SCENARIO
    assert response.payload.target_state == CoreDomain.SCENARIO
    assert response.payload.quest_key == "portal_guide_dialogue"
    assert response.payload.metadata["npc_key"] == "portal_pad_guide"
    assert response.payload.metadata["initial_node_key"] == "death_return_greeting"
    assert response.payload.context["return_context"]["npc_key"] == "portal_pad_guide"
    assert response.payload.context["return_context"]["metadata"]["initial_node_key"] == "death_return_greeting"


@pytest.mark.asyncio
async def test_claim_post_combat_loot_response_uses_integrator_target_state():
    user_id = uuid4()
    session_doc = active_session(
        user_id=user_id,
        state=CoreDomain.LOOT,
        prev_state=CoreDomain.COMBAT_RESULT,
        sessions={"post_combat": {"target_state": "loot", "return_state": "rift", "corpse_ids": ["corpse-1"]}},
    )
    integrator = FakeGameSessionIntegrator(session_doc=session_doc)
    service = GameSessionService(integrator=integrator)

    response = await service.claim_post_combat_loot(SimpleNamespace(id=user_id), 7, ["corpse-1"])

    assert response.header.current_state == CoreDomain.RIFT
    assert response.header.previous_state == CoreDomain.LOOT
    assert response.payload.target_state == CoreDomain.RIFT
    assert response.payload.metadata["target_state"] == "rift"


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


@pytest.mark.asyncio
async def test_integrator_resolves_starter_rift_death_context_only_for_starter_rift():
    session_doc = active_session(
        state=CoreDomain.DEATH,
        prev_state=CoreDomain.COMBAT_RESULT,
        sessions={
            "death_run_id": "run-1",
            "rift_session_id": "rift-run-1",
            "rift_instance_id": "rift-instance-1",
        },
    )
    integrator = GameSessionIntegrator(
        character_sessions=FakeCharacterSessions(),
        rift_runtime=FakeRiftRuntimeForDeath(setting_key="starter_rift"),
    )

    context = await integrator.resolve_starter_rift_death_context(session_doc)

    assert context["rift_key"] == "starter_rift"
    assert context["rift_session_id"] == "rift-run-1"
    assert context["rift_instance_id"] == "rift-instance-1"
    assert context["current_node_id"] == "z01:2_2"
    assert context["active_encounter_id"] == "combat-1"
    assert context["attributes_before"]["strength"] == 8

    non_starter = GameSessionIntegrator(
        character_sessions=FakeCharacterSessions(),
        rift_runtime=FakeRiftRuntimeForDeath(setting_key="deep_rift"),
    )
    assert await non_starter.resolve_starter_rift_death_context(session_doc) is None


@pytest.mark.asyncio
async def test_integrator_resets_starter_rift_character_through_starting_imprint_pipeline():
    sessions = FakeCharacterSessions(
        {
            "char_id": 7,
            "state": CoreDomain.DEATH.value,
            "prev_state": CoreDomain.COMBAT_RESULT.value,
            "attributes": {"strength": 8, "agility": 8, "endurance": 8},
            "vitals": {"hp": {"cur": 0, "max": 100}, "energy": {"cur": 12, "max": 100}, "stamina": {"cur": 0, "max": 100}},
            "sessions": {
                "death_run_id": "run-1",
                "rift_session_id": "rift-run-1",
                "rift_instance_id": "rift-instance-1",
            },
        }
    )
    reset_integration = SimpleNamespace(
        reset_character_to_starting_imprint=AsyncMock(
            return_value={
                "status": "reset",
                "starting_imprint": {"imprint_key": "starter_guard_01", "attributes": {"endurance": 17}},
            }
        )
    )
    integrator = GameSessionIntegrator(character_sessions=sessions, starter_reset_integration=reset_integration)
    starter_context = {
        "rift_key": "starter_rift",
        "rift_session_id": "rift-run-1",
        "rift_instance_id": "rift-instance-1",
        "current_node_id": "z01:2_2",
        "active_encounter_id": "combat-1",
        "attributes_before": {"strength": 8, "agility": 8, "endurance": 8},
        "vitals_before": {"hp": {"cur": 0, "max": 100}},
    }

    user_id = uuid4()
    result = await integrator.reset_starter_rift_character(
        7,
        user_id=user_id,
        starter_context=starter_context,
        respawn_result={"status": "respawned", "location_id": "52_52", "corpse_id": "corpse-1", "run_id": "run-1"},
    )

    assert result["attempt_index"] == 1
    assert result["starting_imprint"]["imprint_key"] == "starter_guard_01"
    reset_integration.reset_character_to_starting_imprint.assert_awaited_once_with(
        user_id=user_id,
        character_id=7,
        seed="starter-rift-reset:7:run-1:1",
    )


@pytest.mark.asyncio
async def test_claim_post_combat_loot_enqueues_claim_job(mocker):
    loot_service_module = import_module("src.backend.features.loot.services.loot_service")
    mocker.patch.object(loot_service_module, "LootService", FakeLootService)
    sessions = FakeCharacterSessions()
    arq = FakeArq()
    integrator = GameSessionIntegrator(character_sessions=sessions, loot_manager=object(), loot_arq=arq)

    result = await integrator.claim_post_combat_loot(7, ["corpse-1"])

    assert result["queued_claims"] == 1
    assert result["target_state"] == "exploration"
    assert arq.jobs == [
        (
            "loot_claim_task",
            {
                "char_id": 7,
                "claims": [
                    {
                        "char_id": 7,
                        "corpse_id": "corpse-1",
                        "instance_ids": ["item-1"],
                        "resource_deltas": {"coin_copper": 3},
                        "summary_items": ["Медные монеты x3", "Ржавый клинок"],
                    }
                ],
                "summary_items": ["Медные монеты x3", "Ржавый клинок"],
                "source_count": 1,
            },
        )
    ]
    assert sessions.patches[-1][1]["$.state"] == CoreDomain.EXPLORATION.value


@pytest.mark.asyncio
async def test_claim_post_combat_loot_batches_multiple_corpses_into_one_claim_job(mocker):
    loot_service_module = import_module("src.backend.features.loot.services.loot_service")
    mocker.patch.object(loot_service_module, "LootService", FakeLootService)
    arq = FakeArq()
    integrator = GameSessionIntegrator(character_sessions=FakeCharacterSessions(), loot_manager=object(), loot_arq=arq)

    result = await integrator.claim_post_combat_loot(7, ["corpse-1", "corpse-2"])

    assert result["queued_claims"] == 2
    assert len(arq.jobs) == 1
    job_name, payload = arq.jobs[0]
    assert job_name == "loot_claim_task"
    assert payload == {
        "char_id": 7,
        "claims": [
            {
                "char_id": 7,
                "corpse_id": "corpse-1",
                "instance_ids": ["item-1"],
                "resource_deltas": {"coin_copper": 3},
                "summary_items": ["Медные монеты x3", "Ржавый клинок"],
            },
            {
                "char_id": 7,
                "corpse_id": "corpse-2",
                "instance_ids": ["item-2"],
                "resource_deltas": {"coin_copper": 3},
                "summary_items": ["Медные монеты x3", "Ржавый клинок"],
            },
        ],
        "summary_items": ["Медные монеты x3", "Ржавый клинок", "Медные монеты x3", "Ржавый клинок"],
        "source_count": 2,
    }


@pytest.mark.asyncio
async def test_claim_post_combat_loot_returns_to_declared_post_loot_state_and_clears_rift(mocker):
    loot_service_module = import_module("src.backend.features.loot.services.loot_service")
    mocker.patch.object(loot_service_module, "LootService", FakeLootService)
    sessions = FakeCharacterSessions(
        {
            "state": CoreDomain.LOOT.value,
            "sessions": {
                "rift_session_id": "rift-run-1",
                "post_combat": {
                    "target_state": "loot",
                    "return_state": "rift",
                    "loot_context": {"rift_session_id": "rift-run-1"},
                },
            },
        }
    )
    rift_runtime = FakeRiftRuntime()
    integrator = GameSessionIntegrator(
        character_sessions=sessions,
        loot_manager=object(),
        loot_arq=FakeArq(),
        rift_runtime=rift_runtime,
    )

    result = await integrator.claim_post_combat_loot(7, ["corpse-1"])

    assert result["target_state"] == "rift"
    assert result["post_combat"]["return_state"] == "rift"
    assert sessions.patches[-1][1] == {
        "$.state": CoreDomain.RIFT.value,
        "$.prev_state": CoreDomain.LOOT.value,
        "$.sessions.post_combat": None,
    }
    assert rift_runtime.applied == [
        {
            "combat_id": "",
            "result": "victory",
            "rift_session_id": "rift-run-1",
            "rift_instance_id": "",
            "event_scope": "",
            "travel_id": "",
            "event_key": "",
            "participant_ref": "",
        }
    ]
    assert rift_runtime.cleared == []


@pytest.mark.asyncio
async def test_claim_post_combat_loot_fails_when_claim_worker_queue_is_unavailable(mocker):
    loot_service_module = import_module("src.backend.features.loot.services.loot_service")
    mocker.patch.object(loot_service_module, "LootService", FakeLootService)
    integrator = GameSessionIntegrator(character_sessions=None, loot_manager=object(), loot_arq=None)

    with pytest.raises(RuntimeError, match="loot_arq is required"):
        await integrator.claim_post_combat_loot(7, ["corpse-1"])
