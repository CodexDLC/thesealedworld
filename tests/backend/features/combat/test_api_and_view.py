import json

import pytest
from fastapi import HTTPException

from src.backend.features.combat.api.router import get_combat_view, register_combat_move
from src.backend.features.combat.integrations import CombatSystemIntegrator
from src.backend.features.combat.orchestrators.runtime_orchestrator import CombatRuntimeOrchestrator
from src.backend.features.combat.services.result_archive_service import CombatResultArchiveService
from src.backend.features.combat.services.session_service import CombatSessionService
from src.shared.enums import CoreDomain
from src.shared.schemas.combat import CombatDashboardDTO, CombatRegisterMoveRequestDTO


@pytest.fixture(autouse=True)
def _skip_combat_move_response_delay(monkeypatch):
    monkeypatch.setattr("src.backend.features.combat.services.session_service.MOVE_RESPONSE_SETTLE_DELAY_SECONDS", 0)


class FakeCombatStore:
    def __init__(self):
        self.exchange_moves = []
        self.instant_moves = []
        self.consumed_feints = []

    async def get_meta(self, session_id):
        return {
            "active": "1",
            "teams": json.dumps({"team_1": ["1"], "team_2": ["2"]}),
            "actors_info": json.dumps({"1": "player", "2": "ai"}),
            "alive_counts": json.dumps({"team_1": 1, "team_2": 1}),
            "dead_actors": "[]",
        }

    async def get_actors_batch(self, session_id, actor_ids):
        actors = {
            str(actor_id): {
                "meta": {
                    "id": str(actor_id),
                    "name": f"Actor {actor_id}",
                    "team": "team_1" if str(actor_id) == "1" else "team_2",
                    "hp": 80,
                    "max_hp": 100,
                    "en": 30,
                    "max_en": 50,
                    "exchange_counter": 2,
                    "type": "player" if str(actor_id) == "1" else "monster",
                    "is_ai": str(actor_id) != "1",
                    "tokens": {"hit": 2, "gift": 1},
                    "feints": {"hand": {"true_strike": {"hit": 1}}},
                },
                "loadout": {
                    "known_abilities": ["fireball"],
                    "belt": [
                        {
                            "item_id": "potion-1",
                            "name": "Small Potion",
                            "belt_slot": "slot_1",
                            "item_type": "consumable",
                        }
                    ]
                },
                "statuses": {
                    "effects": [{"uid": "fx-1", "effect_id": "burn", "expire_at_exchange": 4}],
                    "abilities": [{"uid": "ab-1", "ability_id": "true_strike", "expire_at_exchange": 2}],
                },
            }
            for actor_id in actor_ids
        }
        actors["1"]["meta"]["avatar_url"] = "/static/images/avatars/rook7.png"
        return actors

    async def get_targets(self, session_id):
        return {"1": ["2"], "2": ["1"]}

    async def get_moves_batch(self, session_id, actor_ids):
        return {"1": {"exchange": {}}}

    async def get_logs(self, session_id, *, start=0, stop=-1):
        return [json.dumps({"type": "log", "text": "started", "timestamp": 1, "tags": ["combat"], "data": {"x": 1}})]

    async def get_actor_state(self, session_id, actor_id):
        return {"afk_level": 0}

    async def consume_feint(self, session_id, actor_id, feint_id):
        self.consumed_feints.append((session_id, actor_id, feint_id))
        return {"hit": 1} if feint_id == "true_strike" else None

    async def return_feint(self, session_id, actor_id, feint_id, cost):
        return None

    async def register_exchange_move(self, session_id, actor_id, target_id, move_dto):
        self.exchange_moves.append((session_id, actor_id, target_id, move_dto))
        return True

    async def append_move(self, session_id, actor_id, strategy, move_dto):
        self.instant_moves.append((session_id, actor_id, strategy, move_dto))


class MissingCombatStore(FakeCombatStore):
    async def get_meta(self, session_id):
        return None


class LockedCombatStore(FakeCombatStore):
    async def get_targets(self, session_id):
        return {"1": [], "2": ["1"]}

    async def get_moves_batch(self, session_id, actor_ids):
        return {"1": {"exchange": {"m1": {"move_id": "m1"}}}}


class EmptyTargetCombatStore(FakeCombatStore):
    async def get_targets(self, session_id):
        return {"1": [], "2": ["1"]}


class FakeCombatSystemIntegrator:
    def __init__(self):
        self.recovered = []

    async def resolve_combat_session_for_character(self, char_id):
        return "combat-1"

    async def recover_missing_combat_session(self, char_id, *, combat_id=None):
        self.recovered.append((char_id, combat_id))
        return "exploration"

    async def resolve_return_state_for_character(self, char_id):
        return "exploration"


class FakeCharacterSessions:
    def __init__(self, session):
        self.session = session
        self.patches = []
        self.dirty = []

    async def get_session(self, char_id):
        return self.session

    async def patch_fields(self, char_id, updates):
        self.patches.append((char_id, updates))

    async def mark_dirty(self, char_id, *, reason, paths):
        self.dirty.append((char_id, reason, paths))


class FakeCommitments:
    pass


class FakeEvents:
    async def publish(self, *args, **kwargs):
        return "1-0"


@pytest.mark.asyncio
async def test_combat_session_service_returns_snapshot():
    service = CombatSessionService(store=FakeCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    snapshot = await service.get_snapshot(1)

    assert snapshot["session_id"] == "combat-1"
    assert snapshot["meta"]["teams"] == {"team_1": ["1"], "team_2": ["2"]}
    assert snapshot["targets"]["1"] == ["2"]


@pytest.mark.asyncio
async def test_combat_session_service_returns_logs():
    service = CombatSessionService(store=FakeCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    logs = await service.get_logs(1)

    assert [entry.text for entry in logs.entries] == ["started"]


@pytest.mark.asyncio
async def test_combat_dashboard_exposes_actor_avatar_url():
    service = CombatSessionService(store=FakeCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    dashboard = await service.get_dashboard(1)

    assert dashboard.hero.avatar_url == "/static/images/avatars/rook7.png"


@pytest.mark.asyncio
async def test_combat_view_endpoint_returns_dashboard_payload_type():
    service = CombatSessionService(store=FakeCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    response = await get_combat_view(1, CombatRuntimeOrchestrator(service))

    assert response.payload_type == "CombatDashboard"
    assert isinstance(response.payload, CombatDashboardDTO)


@pytest.mark.asyncio
async def test_combat_view_endpoint_returns_result_payload_type_when_session_missing():
    service = CombatSessionService(store=MissingCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    response = await get_combat_view(1, CombatRuntimeOrchestrator(service))

    assert response.payload_type == "CombatResult"


@pytest.mark.asyncio
async def test_combat_dashboard_derives_session_display_state():
    service = CombatSessionService(store=FakeCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    dashboard = await service.get_dashboard(1)

    assert dashboard.phase == "ACTION_READY"
    assert dashboard.personal_turn_number == 2
    assert dashboard.round_size == 2
    assert dashboard.target_queue_size == 1
    assert dashboard.hero.quick_items[0]["item_id"] == "potion-1"


@pytest.mark.asyncio
async def test_combat_dashboard_exposes_real_actor_contract_and_actions():
    service = CombatSessionService(store=FakeCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    dashboard = await service.get_dashboard(1)

    assert dashboard.session_id == "combat-1"
    assert dashboard.hero.actor_id == "1"
    assert dashboard.target.actor_id == "2"
    assert [actor.actor_id for actor in dashboard.enemies] == ["2"]
    assert dashboard.hero.tokens == {"hit": 2, "gift": 1}
    assert [effect.effect_id for effect in dashboard.hero.active_effects] == ["burn"]
    assert [ability.ability_id for ability in dashboard.hero.active_abilities] == ["true_strike"]
    assert [feint.feint_id for feint in dashboard.hero.feints] == ["true_strike"]
    assert dashboard.events_delta.events[0].data == {"x": 1}


@pytest.mark.asyncio
async def test_available_actions_contains_exchange_and_no_feint_instant_actions():
    service = CombatSessionService(store=FakeCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    dashboard = await service.get_dashboard(1)

    exchange = next(action for action in dashboard.available_actions if action.action == "exchange")
    assert exchange.target_id == "2"
    assert exchange.feint_id is None
    assert exchange.ability_id is None
    assert all(action.feint_id is None for action in dashboard.available_actions if action.action == "instant")
    assert {action.ability_id for action in dashboard.available_actions if action.action == "instant"} == {"fireball"}


@pytest.mark.asyncio
async def test_combat_dashboard_marks_pending_action_as_locked_even_without_queue_target():
    service = CombatSessionService(store=LockedCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    dashboard = await service.get_dashboard(1)

    assert dashboard.target is None
    assert dashboard.pending_action_count == 1
    assert dashboard.action_state == "ACTION_LOCKED"


@pytest.mark.asyncio
async def test_combat_dashboard_marks_empty_queue_only_without_pending_action():
    service = CombatSessionService(store=EmptyTargetCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    dashboard = await service.get_dashboard(1)

    assert dashboard.target is None
    assert dashboard.pending_action_count == 0
    assert dashboard.action_state == "TARGET_QUEUE_EMPTY"


@pytest.mark.asyncio
async def test_post_exchange_accepts_null_feint_id():
    store = FakeCombatStore()
    service = CombatSessionService(store=store, system_integrator=FakeCombatSystemIntegrator())

    await register_combat_move(
        1,
        CombatRegisterMoveRequestDTO(action="exchange", target_id="2", feint_id=None),
        CombatRuntimeOrchestrator(service),
    )

    assert store.exchange_moves[0][2] == "2"
    assert store.exchange_moves[0][3]["payload"]["feint_id"] is None
    assert store.consumed_feints == []


@pytest.mark.asyncio
async def test_post_exchange_requires_target_id_from_client_payload():
    store = FakeCombatStore()
    service = CombatSessionService(store=store, system_integrator=FakeCombatSystemIntegrator())

    with pytest.raises(HTTPException) as exc_info:
        await register_combat_move(
            1,
            CombatRegisterMoveRequestDTO(action="exchange", target_id=None, feint_id=None),
            CombatRuntimeOrchestrator(service),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Target ID is required for exchange"
    assert store.exchange_moves == []


@pytest.mark.asyncio
async def test_post_exchange_accepts_feint_id():
    store = FakeCombatStore()
    service = CombatSessionService(store=store, system_integrator=FakeCombatSystemIntegrator())

    await register_combat_move(
        1,
        CombatRegisterMoveRequestDTO(action="exchange", target_id="2", feint_id="true_strike"),
        CombatRuntimeOrchestrator(service),
    )

    assert store.exchange_moves[0][3]["payload"]["feint_id"] == "true_strike"
    assert store.consumed_feints == [("combat-1", 1, "true_strike")]


@pytest.mark.asyncio
async def test_post_instant_accepts_ability_id():
    store = FakeCombatStore()
    service = CombatSessionService(store=store, system_integrator=FakeCombatSystemIntegrator())

    await register_combat_move(
        1,
        CombatRegisterMoveRequestDTO(action="instant", target_id="2", ability_id="fireball"),
        CombatRuntimeOrchestrator(service),
    )

    assert store.instant_moves[0][2] == "instant"
    assert store.instant_moves[0][3]["payload"]["ability_id"] == "fireball"


@pytest.mark.asyncio
async def test_missing_live_combat_session_recovers_stale_ac_before_fallback():
    integrator = FakeCombatSystemIntegrator()
    service = CombatSessionService(store=MissingCombatStore(), system_integrator=integrator)

    with pytest.raises(ValueError, match="Combat session not found: combat-1"):
        await service.get_dashboard(1)

    assert integrator.recovered == [(1, "combat-1")]


@pytest.mark.asyncio
async def test_combat_recovery_clears_ac_combat_id_and_maps_arena_parent_state():
    sessions = FakeCharacterSessions(
        {
            "state": CoreDomain.COMBAT.value,
            "prev_state": CoreDomain.ARENA.value,
            "sessions": {"combat_id": "combat-1"},
        }
    )
    integrator = CombatSystemIntegrator(
        actor_commitments=FakeCommitments(),
        character_sessions=sessions,
        events=FakeEvents(),
    )

    recovered = await integrator.recover_missing_combat_session(7, combat_id="combat-1")

    assert recovered == CoreDomain.ARENA.value
    assert sessions.patches == [
        (
            7,
            {
                "$.sessions.combat_id": None,
                "$.prev_state": CoreDomain.EXPLORATION.value,
                "$.state": CoreDomain.ARENA.value,
            },
        )
    ]
    assert sessions.dirty == [
        (
            7,
            "combat_session_missing_recovered",
            ["$.prev_state", "$.sessions.combat_id", "$.state"],
        )
    ]


@pytest.mark.asyncio
async def test_combat_recovery_falls_back_to_exploration_when_previous_state_is_combat():
    sessions = FakeCharacterSessions(
        {
            "state": CoreDomain.COMBAT.value,
            "prev_state": CoreDomain.COMBAT.value,
            "sessions": {"combat_id": "combat-1"},
        }
    )
    integrator = CombatSystemIntegrator(
        actor_commitments=FakeCommitments(),
        character_sessions=sessions,
        events=FakeEvents(),
    )

    recovered = await integrator.recover_missing_combat_session(7, combat_id="combat-1")

    assert recovered == CoreDomain.EXPLORATION.value
    assert sessions.patches[0][1]["$.state"] == CoreDomain.EXPLORATION.value
    assert sessions.patches[0][1]["$.prev_state"] is None


@pytest.mark.asyncio
async def test_archived_result_uses_recovered_return_state_for_primary_action():
    class ArenaReturnIntegrator(FakeCombatSystemIntegrator):
        async def resolve_return_state_for_character(self, char_id):
            return CoreDomain.ARENA.value

    service = CombatSessionService(store=MissingCombatStore(), system_integrator=ArenaReturnIntegrator())

    result = await service.get_archived_result(1)

    assert result.primary_action.target_state == CoreDomain.ARENA.value


@pytest.mark.asyncio
async def test_combat_archive_stub_returns_result_contract():
    result = await CombatResultArchiveService().get_result_for_character(1, combat_id="combat-1")

    assert result.char_id == 1
    assert result.combat_id == "combat-1"
    assert result.archived is False
    assert result.metadata["source"] == "combat_archive_stub"
    assert result.primary_action.action == "navigate"
    assert result.primary_action.target_state == "exploration"
