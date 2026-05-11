import json

import pytest
from fastapi import HTTPException

from src.backend.features.character.events import CharacterEvents
from src.backend.features.combat.api.router import (
    continue_combat_result,
    get_combat_view,
    pin_combat_feint,
    register_combat_move,
)
from src.backend.features.combat.integrations import CombatSystemIntegrator
from src.backend.features.combat.orchestrators.runtime_orchestrator import CombatRuntimeOrchestrator
from src.backend.features.combat.services.result_archive_service import CombatResultArchiveService
from src.backend.features.combat.services.session_service import CombatSessionService
from src.backend.features.combat.services.view_service import CombatViewService
from src.shared.enums import CoreDomain
from src.shared.schemas.combat import (
    CombatDashboardDTO,
    CombatPinFeintRequestDTO,
    CombatRegisterMoveRequestDTO,
    CombatResultDTO,
)


@pytest.fixture(autouse=True)
def _skip_combat_move_response_delay(monkeypatch):
    monkeypatch.setattr("src.backend.features.combat.services.session_service.MOVE_RESPONSE_SETTLE_DELAY_SECONDS", 0)


class FakeCombatStore:
    def __init__(self):
        self.exchange_moves = []
        self.instant_moves = []
        self.consumed_feints = []
        self.pinned_feints = []
        self.touched_sessions = []

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

    async def get_logs_by_turn(self, session_id):
        return {
            "1": [
                json.dumps(
                    {
                        "type": "log",
                        "text": "started",
                        "timestamp": 1,
                        "tags": ["combat"],
                        "data": {"x": 1, "global_turn": 1},
                        "global_turn": 1,
                    }
                )
            ]
        }

    async def get_actor_state(self, session_id, actor_id):
        return {"afk_level": 0}

    async def consume_feint(self, session_id, actor_id, feint_id):
        self.consumed_feints.append((session_id, actor_id, feint_id))
        return {"hit": 1} if feint_id == "true_strike" else None

    async def return_feint(self, session_id, actor_id, feint_id, cost):
        return None

    async def pin_feint(self, session_id, actor_id, feint_id):
        self.pinned_feints.append((session_id, actor_id, feint_id))
        return feint_id in ("true_strike", None)

    async def register_exchange_move(self, session_id, actor_id, target_id, move_dto):
        self.exchange_moves.append((session_id, actor_id, target_id, move_dto))
        return True

    async def append_move(self, session_id, actor_id, strategy, move_dto):
        self.instant_moves.append((session_id, actor_id, strategy, move_dto))

    async def touch_activity(self, session_id):
        self.touched_sessions.append(session_id)


class MissingCombatStore(FakeCombatStore):
    async def get_meta(self, session_id):
        return None


class FinishedCombatStore(FakeCombatStore):
    async def get_meta(self, session_id):
        meta = await super().get_meta(session_id)
        return {**meta, "active": "0", "status": "finished", "winner": "team_1"}


class FinalizedCombatStore(FinishedCombatStore):
    async def get_finalization(self, session_id):
        return {
            "schema_version": 1,
            "combat_id": session_id,
            "status": "finalized",
            "winner_team": "team_1",
            "participant_char_ids": [1],
            "meta": {"battle_type": "pve", "source": "exploration"},
            "teams": {"team_1": ["1"], "team_2": ["2"]},
            "actors": {
                "1": {
                    "actor_id": "1",
                    "char_id": 1,
                    "name": "Hero",
                    "team": "team_1",
                    "actor_type": "player",
                    "is_dead": False,
                    "xp_buffer": {"main_hand_hit": 1},
                    "progression": {"skill_swords": 0.0003},
                },
                "2": {
                    "actor_id": "2",
                    "char_id": None,
                    "name": "Wolf",
                    "team": "team_2",
                    "actor_type": "monster",
                    "is_dead": True,
                    "xp_buffer": {},
                    "progression": {},
                },
            },
            "report": {
                "last_turn": 3,
                "teams": [
                    {"team": "team_1", "outcome": "victory", "actors": [{"actor_id": "1", "name": "Hero"}]},
                    {"team": "team_2", "outcome": "defeat", "actors": [{"actor_id": "2", "name": "Wolf"}]},
                ],
            },
            "analytics": {"3:0": {"o": "H"}},
            "reward_hooks": [{"type": "loot.roll", "status": "pending"}],
        }


class FinalizedCombatStoreWithoutReportTeams(FinalizedCombatStore):
    async def get_finalization(self, session_id):
        finalization = await super().get_finalization(session_id)
        finalization["report"] = {"last_turn": 3}
        return finalization


class FinishesAfterMoveCombatStore(FakeCombatStore):
    async def get_meta(self, session_id):
        meta = await super().get_meta(session_id)
        if self.exchange_moves or self.instant_moves:
            return {**meta, "active": "0", "status": "finished", "winner": "team_1"}
        return meta


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
        self.completed_returns = []
        self.marked_finalized = []
        self.finalization_id = None

    async def resolve_combat_session_for_character(self, char_id):
        return "combat-1"

    async def resolve_combat_finalization_for_character(self, char_id):
        return self.finalization_id

    async def mark_combat_finalized(self, char_id, combat_id):
        self.marked_finalized.append((char_id, combat_id))

    async def recover_missing_combat_session(self, char_id, *, combat_id=None):
        self.recovered.append((char_id, combat_id))
        return "exploration"

    async def complete_combat_session_return(self, char_id, *, combat_id=None):
        self.completed_returns.append((char_id, combat_id))
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
    def __init__(self):
        self.requests = []

    async def publish(self, *args, **kwargs):
        return "1-0"

    async def request(self, event_type, payload, *, timeout=None):
        self.requests.append((event_type, payload, timeout))
        return {"status": "ok"}


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
    assert logs.turns[0].global_turn == 1
    assert [entry.text for entry in logs.turns[0].entries] == ["started"]


def test_combat_view_service_collapses_fragmented_entries_into_turn_blocks():
    service = CombatViewService()
    turns = service.parse_logs_by_turn(
        {
            "unknown-1": ['{"type":"RESULT","text":"Ход 1. A атакует B.","timestamp":1}'],
            "unknown-2": ['{"type":"RESULT","text":"B парирует.","timestamp":2}'],
            "unknown-3": ['{"type":"RESULT","text":"Ход 1. B отвечает A.","timestamp":3}'],
            "unknown-4": ['{"type":"RESULT","text":"A получает 4 урона.","timestamp":4}'],
        }
    )

    assert len(turns) == 1
    assert turns[0].global_turn == 1
    assert [entry.text for entry in turns[0].entries] == [
        "A атакует B.",
        "B парирует.",
        "B отвечает A.",
        "A получает 4 урона.",
    ]


def test_combat_view_service_returns_latest_turn_first():
    service = CombatViewService()
    turns = service.parse_logs_by_turn(
        {
            "1": ['{"type":"RESULT","text":"Ход 1. first","timestamp":1}'],
            "2": ['{"type":"RESULT","text":"Ход 2. second","timestamp":2}'],
        }
    )

    assert [turn.global_turn for turn in turns] == [2, 1]
    assert [turn.entries[0].text for turn in turns] == ["second", "first"]


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

    assert response.payload_type == "state_transition"
    assert response.header.current_state == CoreDomain.EXPLORATION


@pytest.mark.asyncio
async def test_combat_view_endpoint_returns_result_payload_type_when_live_session_finished():
    service = CombatSessionService(store=FinishedCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    response = await get_combat_view(1, CombatRuntimeOrchestrator(service))

    assert response.payload_type == "CombatResult"
    assert isinstance(response.payload, CombatResultDTO)
    assert response.payload.reason == "combat_session_finished"
    assert response.payload.status == "finished"
    assert response.payload.outcome == "victory"
    assert response.payload.archived is True
    assert response.payload.metadata["source"] == "combat_runtime_history"


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
    assert dashboard.hero.tokens == {"hit": 3, "gift": 1}
    assert [effect.effect_id for effect in dashboard.hero.active_effects] == ["burn"]
    assert [ability.ability_id for ability in dashboard.hero.active_abilities] == ["true_strike"]
    assert [feint.feint_id for feint in dashboard.hero.feints] == ["true_strike"]
    assert dashboard.events_delta.events[0].data["x"] == 1
    assert dashboard.events_delta.turns[0].global_turn == 1


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
    assert exc_info.value.error_code == "combat_target_required"
    assert exc_info.value.extra["domain"] == "combat"
    assert exc_info.value.extra["frontend_action"] == "show_message"
    assert exc_info.value.extra["context"]["char_id"] == 1
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
async def test_post_exchange_returns_result_when_move_finishes_session():
    service = CombatSessionService(store=FinishesAfterMoveCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    result = await register_combat_move(
        1,
        CombatRegisterMoveRequestDTO(action="exchange", target_id="2", feint_id=None),
        CombatRuntimeOrchestrator(service),
    )

    assert isinstance(result, CombatResultDTO)
    assert result.reason == "combat_session_finished"
    assert result.status == "finished"
    assert result.outcome == "victory"
    assert result.archived is True


@pytest.mark.asyncio
async def test_archived_result_uses_finished_runtime_history_before_stub():
    service = CombatSessionService(store=FinishedCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    result = await service.get_archived_result(1, reason="combat_session_finished")

    assert result.char_id == 1
    assert result.combat_id == "combat-1"
    assert result.status == "finished"
    assert result.outcome == "victory"
    assert result.title == "Победа"
    assert result.archived is True
    assert result.metadata["source"] == "combat_runtime_history"
    assert result.metadata["winner"] == "team_1"
    assert result.metadata["viewer_team"] == "team_1"
    assert result.metadata["last_turn"] == 1
    assert "Последний ход в журнале: 1." in result.summary


@pytest.mark.asyncio
async def test_archived_result_prefers_combat_finalization_before_runtime_history():
    service = CombatSessionService(store=FinalizedCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    result = await service.get_archived_result(1, reason="combat_session_finished")

    assert result.char_id == 1
    assert result.combat_id == "combat-1"
    assert result.status == "finished"
    assert result.outcome == "victory"
    assert result.archived is True
    assert result.metadata["source"] == "combat_finalization"
    assert result.metadata["battle_type"] == "pve"
    assert result.report["last_turn"] == 3
    assert result.actors["1"]["progression"] == {"skill_swords": 0.0003}
    assert result.rewards == {"progression": {"skill_swords": 0.0003}}
    assert result.reward_hooks == [{"type": "loot.roll", "status": "pending"}]


@pytest.mark.asyncio
async def test_archived_finalization_completes_missing_report_teams_from_actor_snapshot():
    service = CombatSessionService(
        store=FinalizedCombatStoreWithoutReportTeams(),
        system_integrator=FakeCombatSystemIntegrator(),
    )

    result = await service.get_archived_result(1, reason="combat_session_finished")

    assert result.metadata["source"] == "combat_finalization"
    assert result.summary == "Ваша команда победила. Последний ход в журнале: 3."
    assert result.report["teams"] == [
        {
            "team": "team_1",
            "outcome": "victory",
            "actors": [{"actor_id": "1", "name": "Hero", "actor_type": "player", "is_dead": False}],
        },
        {
            "team": "team_2",
            "outcome": "defeat",
            "actors": [{"actor_id": "2", "name": "Wolf", "actor_type": "monster", "is_dead": True}],
        },
    ]


@pytest.mark.asyncio
async def test_post_pin_feint_accepts_single_hand_option():
    store = FakeCombatStore()
    service = CombatSessionService(store=store, system_integrator=FakeCombatSystemIntegrator())

    dashboard = await pin_combat_feint(
        1,
        CombatPinFeintRequestDTO(feint_id="true_strike"),
        CombatRuntimeOrchestrator(service),
    )

    assert isinstance(dashboard, CombatDashboardDTO)
    assert store.pinned_feints == [("combat-1", 1, "true_strike")]


@pytest.mark.asyncio
async def test_post_pin_feint_rejects_missing_hand_option():
    store = FakeCombatStore()
    service = CombatSessionService(store=store, system_integrator=FakeCombatSystemIntegrator())

    with pytest.raises(HTTPException) as exc_info:
        await pin_combat_feint(
            1,
            CombatPinFeintRequestDTO(feint_id="missing"),
            CombatRuntimeOrchestrator(service),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Feint is not in hand"
    assert exc_info.value.error_code == "combat_feint_unavailable"
    assert exc_info.value.extra["domain"] == "combat"
    assert exc_info.value.extra["context"] == {"feint_id": "missing", "char_id": 1}


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

    assert integrator.recovered == []


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
                "$.sessions.combat_finalization_id": None,
                "$.prev_state": CoreDomain.EXPLORATION.value,
                "$.state": CoreDomain.ARENA.value,
            },
        )
    ]
    assert sessions.dirty == [
        (
            7,
            "combat_session_missing_recovered",
            ["$.prev_state", "$.sessions.combat_finalization_id", "$.sessions.combat_id", "$.state"],
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
async def test_archived_result_completes_combat_return_state() -> None:
    integrator = FakeCombatSystemIntegrator()
    service = CombatSessionService(store=FinalizedCombatStore(), system_integrator=integrator)

    result = await service.get_archived_result(1, reason="combat_session_finished")

    assert result.primary_action.target_state == CoreDomain.EXPLORATION.value
    assert integrator.completed_returns == []
    assert integrator.marked_finalized == [(1, "combat-1")]


@pytest.mark.asyncio
async def test_combat_finalized_return_clears_ac_and_syncs_to_db() -> None:
    events = FakeEvents()
    sessions = FakeCharacterSessions(
        {
            "state": CoreDomain.COMBAT.value,
            "prev_state": CoreDomain.EXPLORATION.value,
            "sessions": {"combat_id": "combat-1"},
        }
    )
    integrator = CombatSystemIntegrator(
        actor_commitments=FakeCommitments(),
        character_sessions=sessions,
        events=events,
    )

    returned = await integrator.complete_combat_session_return(7, combat_id="combat-1")

    assert returned == CoreDomain.EXPLORATION.value
    assert sessions.patches == [
        (
            7,
            {
                "$.sessions.combat_id": None,
                "$.sessions.combat_finalization_id": None,
                "$.prev_state": None,
                "$.state": CoreDomain.EXPLORATION.value,
            },
        )
    ]
    assert sessions.dirty == [
        (
            7,
            "combat_session_finalized_returned",
            ["$.prev_state", "$.sessions.combat_finalization_id", "$.sessions.combat_id", "$.state"],
        )
    ]
    assert events.requests == [
        (
            CharacterEvents.ACTIVE_SESSION_SYNC_REQUESTED,
            {"char_id": 7},
            30.0,
        )
    ]


@pytest.mark.asyncio
async def test_continue_combat_result_clears_ac_and_returns_transition() -> None:
    events = FakeEvents()
    sessions = FakeCharacterSessions(
        {
            "state": CoreDomain.COMBAT_RESULT.value,
            "prev_state": CoreDomain.ARENA.value,
            "sessions": {"combat_id": None, "combat_finalization_id": "combat-1"},
        }
    )
    service = CombatSessionService(
        store=FinalizedCombatStore(),
        system_integrator=CombatSystemIntegrator(
            actor_commitments=FakeCommitments(),
            character_sessions=sessions,
            events=events,
        ),
    )

    response = await continue_combat_result(7, CombatRuntimeOrchestrator(service))

    assert response.payload_type == "state_transition"
    assert response.header.current_state == CoreDomain.ARENA
    assert response.payload.target_state == CoreDomain.ARENA
    assert sessions.patches[0][1]["$.sessions.combat_finalization_id"] is None
    assert sessions.patches[0][1]["$.sessions.combat_id"] is None


@pytest.mark.asyncio
async def test_combat_archive_stub_returns_result_contract():
    result = await CombatResultArchiveService().get_result_for_character(1, combat_id="combat-1")

    assert result.char_id == 1
    assert result.combat_id == "combat-1"
    assert result.archived is False
    assert result.metadata["source"] == "combat_archive_stub"
    assert result.primary_action.action == "navigate"
    assert result.primary_action.target_state == "exploration"
