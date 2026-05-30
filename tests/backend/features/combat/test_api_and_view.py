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
        self.seeded_initial_ai_sessions = []
        self.started_sessions = []

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
                    "known_abilities": ["fireball", "basic_punish_mistake"],
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
        actors["1"]["meta"]["avatar_url"] = "/static/images/avatars/rook7.webp"
        actors["2"]["meta"]["tags"] = ["monster", "rat_swarm"]
        actors["2"]["meta"]["role"] = "minion"
        actors["2"]["meta"]["template_id"] = "sewer_rat"
        actors["2"]["meta"]["archetype"] = "beast"
        actors["2"]["source"] = {
            "monster_id": "m-2",
            "family_id": "rat_swarm",
            "visual": {
                "image_url": "/static/generated-assets/monsters/generated/members/rat.webp",
                "asset_hash": "rat-image-bytes",
            },
        }
        return actors

    async def get_targets(self, session_id):
        return {"1": ["2"], "2": ["1"]}

    async def get_moves_batch(self, session_id, actor_ids):
        return {"1": {"exchange": {}}}

    async def seed_initial_ai_turns_on_dashboard(self, *, session_id, viewer_id, meta, actors, targets, moves):
        if meta.get("started_at"):
            return False
        teams = json.loads(meta.get("teams", "{}"))
        if str(viewer_id) not in {str(member) for members in teams.values() for member in members}:
            return False
        if session_id in self.seeded_initial_ai_sessions:
            return False
        actors_info = json.loads(meta.get("actors_info", "{}"))
        dead_actors = {str(actor_id) for actor_id in json.loads(meta.get("dead_actors", "[]"))}
        for actor_id, actor_type in actors_info.items():
            actor_id = str(actor_id)
            actor_state = actors.get(actor_id, {})
            actor_meta = actor_state.get("meta", {})
            has_live_target = any(
                str(target_id) not in dead_actors
                and actors.get(str(target_id), {}).get("meta", {}).get("hp", 0) > 0
                for target_id in targets.get(actor_id, [])
            )
            if actor_type == "ai" and actor_id not in dead_actors and actor_meta.get("hp", 0) > 0 and has_live_target:
                self.seeded_initial_ai_sessions.append(session_id)
                return True
        return False

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
        return {"afk_level": 0, "stamina": 100, "max_stamina": 100}

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

    async def mark_started_and_refresh_ttl(self, session_id):
        if session_id in self.started_sessions:
            return False
        self.started_sessions.append(session_id)
        return True


class MissingCombatStore(FakeCombatStore):
    async def get_meta(self, session_id):
        return None


class NoAiCombatStore(FakeCombatStore):
    async def get_meta(self, session_id):
        meta = await super().get_meta(session_id)
        return {**meta, "actors_info": json.dumps({"1": "player", "2": "player"})}


class LowStaminaCombatStore(FakeCombatStore):
    def __init__(self):
        super().__init__()
        self.returned_feints = []

    async def get_actor_state(self, session_id, actor_id):
        return {"afk_level": 0, "stamina": 4, "max_stamina": 100}

    async def return_feint(self, session_id, actor_id, feint_id, cost):
        self.returned_feints.append((session_id, actor_id, feint_id, cost))


class FinishedCombatStore(FakeCombatStore):
    async def get_meta(self, session_id):
        meta = await super().get_meta(session_id)
        return {**meta, "active": "0", "status": "finished", "winner": "team_1"}


class UnorderedCombatLogStore(FakeCombatStore):
    async def get_logs_by_turn(self, session_id):
        return {
            "14": [json.dumps({"type": "RESULT", "text": "Ход 14. latest", "global_turn": 14})],
            "6": [json.dumps({"type": "RESULT", "text": "Ход 6. older", "global_turn": 6})],
            "10": [json.dumps({"type": "RESULT", "text": "Ход 10. old", "global_turn": 10})],
            "5": [json.dumps({"type": "RESULT", "text": "Ход 5. older", "global_turn": 5})],
            "13": [json.dumps({"type": "RESULT", "text": "Ход 13. latest", "global_turn": 13})],
            "1": [json.dumps({"type": "RESULT", "text": "Ход 1. oldest", "global_turn": 1})],
            "12": [json.dumps({"type": "RESULT", "text": "Ход 12. latest", "global_turn": 12})],
            "11": [json.dumps({"type": "RESULT", "text": "Ход 11. latest", "global_turn": 11})],
            "7": [json.dumps({"type": "RESULT", "text": "Ход 7. older", "global_turn": 7})],
            "8": [json.dumps({"type": "RESULT", "text": "Ход 8. older", "global_turn": 8})],
            "9": [json.dumps({"type": "RESULT", "text": "Ход 9. older", "global_turn": 9})],
            "2": [json.dumps({"type": "RESULT", "text": "Ход 2. oldest", "global_turn": 2})],
            "4": [json.dumps({"type": "RESULT", "text": "Ход 4. oldest", "global_turn": 4})],
            "3": [json.dumps({"type": "RESULT", "text": "Ход 3. oldest", "global_turn": 3})],
        }


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


class WaitingResponseCombatStore(FakeCombatStore):
    async def get_moves_batch(self, session_id, actor_ids):
        return {"1": {"exchange": {"m1": {"move_id": "m1", "payload": {"target_id": "2"}}}}}


class OpponentRespondedCombatStore(FakeCombatStore):
    async def get_moves_batch(self, session_id, actor_ids):
        return {
            "1": {"exchange": {"m1": {"move_id": "m1", "payload": {"target_id": "2"}}}},
            "2": {"exchange": {"m2": {"move_id": "m2", "payload": {"target_id": "1"}}}},
        }


class OpponentDeadlineCombatStore(FakeCombatStore):
    async def get_moves_batch(self, session_id, actor_ids):
        return {
            "2": {
                "exchange": {
                    "m2": {
                        "move_id": "m2",
                        "payload": {"target_id": "1"},
                        "registered_at_ms": 1_000_000,
                        "timeout_ms": 60_000,
                        "force_attack_at_ms": 1_025_000,
                    }
                }
            }
        }


class EmptyTargetCombatStore(FakeCombatStore):
    async def get_targets(self, session_id):
        return {"1": [], "2": ["1"]}


class DeadFirstTargetCombatStore(FakeCombatStore):
    async def get_meta(self, session_id):
        meta = await super().get_meta(session_id)
        return {
            **meta,
            "teams": json.dumps({"team_1": ["1"], "team_2": ["2", "3"]}),
            "actors_info": json.dumps({"1": "player", "2": "ai", "3": "ai"}),
            "dead_actors": json.dumps(["2"]),
        }

    async def get_targets(self, session_id):
        return {"1": ["2", "3"], "2": ["1"], "3": ["1"]}

    async def get_actor_state(self, session_id, actor_id):
        if str(actor_id) == "2":
            return {"hp": 0, "is_dead": True, "afk_level": 0}
        return {"hp": 80, "is_dead": False, "afk_level": 0}


class DeadViewerTeamCombatStore(FakeCombatStore):
    async def get_meta(self, session_id):
        meta = await super().get_meta(session_id)
        return {
            **meta,
            "dead_actors": json.dumps(["1"]),
            "alive_counts": json.dumps({"team_1": 0, "team_2": 1}),
        }

    async def get_actor_state(self, session_id, actor_id):
        if str(actor_id) == "1":
            return {"hp": 0, "is_dead": True, "afk_level": 0}
        return {"hp": 80, "is_dead": False, "afk_level": 0}


class LatestFinalizedCombatStore(FinalizedCombatStore):
    async def get_latest_finalization_id_for_character(self, char_id):
        return "combat-1"


class CapturingArqQueue:
    def __init__(self):
        self.jobs = []

    async def enqueue_job(self, function, *args, **kwargs):
        self.jobs.append((function, args, kwargs))


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


class FinalizationOnlyCombatSystemIntegrator(FakeCombatSystemIntegrator):
    def __init__(self):
        super().__init__()
        self.finalization_id = "combat-1"

    async def resolve_combat_session_for_character(self, char_id):
        return None


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


class FakeRiftRuntime:
    def __init__(self):
        self.cleared = []
        self.applied = []

    async def clear_run_active_encounter(self, rift_session_id):
        self.cleared.append(rift_session_id)

    async def apply_combat_result(self, **kwargs):
        self.applied.append(kwargs)
        return {"applied": True}


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


@pytest.mark.asyncio
async def test_combat_logs_page_uses_latest_turns_when_storage_order_is_unstable():
    service = CombatSessionService(store=UnorderedCombatLogStore(), system_integrator=FakeCombatSystemIntegrator())

    logs = await service.get_logs(1, page=1, page_size=4)

    assert [turn.global_turn for turn in logs.turns] == [14, 13, 12, 11]


@pytest.mark.asyncio
async def test_combat_logs_fallback_to_finalization_when_active_session_is_gone():
    service = CombatSessionService(
        store=FakeCombatStore(),
        system_integrator=FinalizationOnlyCombatSystemIntegrator(),
    )

    logs = await service.get_logs(1)

    assert [entry.text for entry in logs.entries] == ["started"]
    assert logs.session_id == "combat-1"
    assert logs.turns[0].global_turn == 1


@pytest.mark.asyncio
async def test_combat_dashboard_uses_latest_turns_when_storage_order_is_unstable():
    service = CombatSessionService(store=UnorderedCombatLogStore(), system_integrator=FakeCombatSystemIntegrator())

    dashboard = await service.get_dashboard(1)

    assert dashboard.events_delta.turns[0].global_turn == 14
    assert dashboard.events_delta.turns[1].global_turn == 13


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


def test_combat_view_service_ignores_monster_family_visual_as_avatar():
    dashboard = CombatViewService().build_dashboard(
        session_id="combat-family-fallback",
        viewer_id=1,
        meta={
            "active": "1",
            "teams": json.dumps({"team_1": ["1"], "team_2": ["2"]}),
            "actors_info": json.dumps({"1": "player", "2": "ai"}),
            "alive_counts": json.dumps({"team_1": 1, "team_2": 1}),
            "dead_actors": "[]",
        },
        targets={"1": ["2"], "2": ["1"]},
        actors={
            "1": {
                "meta": {"id": "1", "name": "Hero", "team": "team_1", "type": "player", "hp": 10, "max_hp": 10},
            },
            "2": {
                "meta": {
                    "id": "2",
                    "name": "Bandit",
                    "team": "team_2",
                    "type": "monster",
                    "hp": 10,
                    "max_hp": 10,
                    "avatar_url": "/static/images/monsters/families/bandit_gang.svg",
                },
                "source": {
                    "visual": {
                        "status": "fallback",
                        "image_url": "/static/images/monsters/families/bandit_gang.svg",
                        "generated_image_url": "/static/generated-assets/monsters/generated/members/not-ready.webp",
                        "fallback_image_url": "/static/images/monsters/families/bandit_gang.svg",
                    }
                },
            },
        },
        raw_logs=[],
    )

    assert dashboard.target is not None
    assert dashboard.target.avatar_url is None


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

    assert dashboard.hero.avatar_url == "/static/images/avatars/rook7.webp"


@pytest.mark.asyncio
async def test_combat_dashboard_exposes_actor_metadata():
    service = CombatSessionService(store=FakeCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    dashboard = await service.get_dashboard(1)

    assert dashboard.target is not None
    assert dashboard.target.archetype == "beast"
    assert dashboard.target.role == "minion"
    assert dashboard.target.template_id == "sewer_rat"
    assert dashboard.target.tags == ["monster", "rat_swarm"]
    assert dashboard.target.source["family_id"] == "rat_swarm"
    assert dashboard.target.visual["image_url"] == "/static/generated-assets/monsters/generated/members/rat.webp"
    assert dashboard.target.avatar_url == "/static/generated-assets/monsters/generated/members/rat.webp?v=rat-image-bytes"


@pytest.mark.asyncio
async def test_combat_dashboard_seeds_initial_ai_once():
    store = FakeCombatStore()
    arq = CapturingArqQueue()
    service = CombatSessionService(store=store, system_integrator=FakeCombatSystemIntegrator(), arq=arq)

    await service.get_dashboard(1)
    await service.get_dashboard(1)

    assert store.seeded_initial_ai_sessions == ["combat-1"]
    assert [job[0] for job in arq.jobs] == ["combat_collector_task"]
    assert arq.jobs[0][1][0]["signal_type"] == "heartbeat"
    assert arq.jobs[0][1][0]["move_id"] == "initial_ai_seed"


@pytest.mark.asyncio
async def test_combat_dashboard_does_not_seed_without_ai():
    store = NoAiCombatStore()
    arq = CapturingArqQueue()
    service = CombatSessionService(store=store, system_integrator=FakeCombatSystemIntegrator(), arq=arq)

    await service.get_dashboard(1)

    assert store.seeded_initial_ai_sessions == []
    assert arq.jobs == []


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
    assert dashboard.hero.tokens == {"hit": 2, "gift": 1}
    assert [effect.effect_id for effect in dashboard.hero.active_effects] == ["burn"]
    assert [ability.ability_id for ability in dashboard.hero.active_abilities] == ["true_strike"]
    assert [feint.feint_id for feint in dashboard.hero.feints] == ["true_strike"]
    assert dashboard.hero.feints[0].cost == {"hit": 1}
    assert dashboard.events_delta.events[0].data["x"] == 1
    assert dashboard.events_delta.turns[0].global_turn == 1


def test_combat_view_enriches_reactive_effect_badges_from_catalog():
    service = CombatViewService()

    dashboard = service.build_dashboard(
        session_id="combat-1",
        viewer_id=1,
        meta={
            "active": "1",
            "teams": json.dumps({"team_1": ["1"], "team_2": ["2"]}),
            "actors_info": json.dumps({"1": "player", "2": "ai"}),
        },
        targets={"1": ["2"], "2": ["1"]},
        actors={
            "1": {
                "meta": {
                    "id": "1",
                    "name": "Hero",
                    "team": "team_1",
                    "hp": 30,
                    "max_hp": 40,
                    "exchange_counter": 6,
                },
                "statuses": {
                    "effects": [
                        {
                            "uid": "fx-riposte",
                            "effect_id": "prep_parry_riposte",
                            "expire_at_exchange": 1004,
                        }
                    ]
                },
            },
            "2": {
                "meta": {
                    "id": "2",
                    "name": "Shadow",
                    "team": "team_2",
                    "hp": 40,
                    "max_hp": 40,
                }
            },
        },
        raw_logs=[],
    )

    effect = dashboard.hero.active_effects[0]
    assert effect.title == "Готовый рипост"
    assert effect.description == "Следующее успешное парирование получает повышенный шанс контратаки."
    assert effect.duration_label == "до следующего парирования"


def test_combat_view_builds_flat_actor_stat_sheet_from_stats_and_attributes():
    service = CombatViewService()

    dashboard = service.build_dashboard(
        session_id="combat-1",
        viewer_id=1,
        meta={
            "active": "1",
            "teams": json.dumps({"team_1": ["1"], "team_2": ["2"]}),
            "actors_info": json.dumps({"1": "player", "2": "ai"}),
        },
        targets={"1": ["2"], "2": ["1"]},
        actors={
            "1": {
                "meta": {"id": "1", "name": "Hero", "team": "team_1", "hp": 30, "max_hp": 40},
                "raw": {
                    "attributes": {
                        "strength": {"base": 10, "source": {"item": "+2"}, "temp": {}},
                        "perception": {"base": 4, "source": {}, "temp": {}},
                        "dexterity": {"base": 0, "source": {}, "temp": {}},
                    },
                    "modifiers": {},
                    "rules": {},
                },
                "stats": {
                    "mods": {
                        "accuracy": 12.5,
                        "main_hand_damage_base": 14,
                        "main_hand_damage_spread": 0.25,
                        "parry": 0,
                        "block": 8,
                        "attack_speed": 3,
                    },
                    "skills": {"skill_parrying": 99},
                },
            },
            "2": {
                "meta": {"id": "2", "name": "Shadow", "team": "team_2", "hp": 40, "max_hp": 40},
                "stats": {"mods": {"armor": 11}},
            },
        },
        raw_logs=[],
    )

    assert dashboard.hero.stat_sheet is not None
    assert [section.key for section in dashboard.hero.stat_sheet.sections] == [
        "offense",
        "defense",
        "attributes",
    ]
    sections = {section.key: section for section in dashboard.hero.stat_sheet.sections}
    assert sections["offense"].items[0].key == "main_hand_damage"
    assert [item.key for item in sections["attributes"].items] == ["strength", "perception"]
    assert sections["attributes"].items[0].value == 12
    assert [item.key for item in sections["defense"].items] == ["block"]
    all_keys = {item.key for section in dashboard.hero.stat_sheet.sections for item in section.items}
    assert "accuracy" not in all_keys
    assert "attack_speed" not in all_keys
    assert "skill_parrying" not in all_keys


@pytest.mark.asyncio
async def test_available_actions_contains_exchange_and_no_feint_instant_actions():
    service = CombatSessionService(store=FakeCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    dashboard = await service.get_dashboard(1)

    exchange = next(action for action in dashboard.available_actions if action.action == "exchange")
    assert exchange.target_id == "2"
    assert exchange.feint_id is None
    assert exchange.ability_id is None
    assert all(action.feint_id is None for action in dashboard.available_actions if action.action == "instant")
    instant_actions = {action.ability_id: action for action in dashboard.available_actions if action.action == "instant"}
    assert set(instant_actions) == {"fireball", "basic_punish_mistake"}
    assert instant_actions["fireball"].enabled is True
    assert instant_actions["basic_punish_mistake"].enabled is False


@pytest.mark.asyncio
async def test_combat_dashboard_marks_pending_action_as_locked_even_without_queue_target():
    service = CombatSessionService(store=LockedCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    dashboard = await service.get_dashboard(1)

    assert dashboard.target is None
    assert dashboard.pending_action_count == 1
    assert dashboard.action_state == "ACTION_LOCKED"
    assert dashboard.exchange_state is not None
    assert dashboard.exchange_state.pair_status == "waiting_response"


@pytest.mark.asyncio
async def test_combat_dashboard_exchange_state_waits_for_opponent_response():
    service = CombatSessionService(store=WaitingResponseCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    dashboard = await service.get_dashboard(1)

    assert dashboard.action_state == "ACTION_LOCKED"
    assert dashboard.exchange_state is not None
    assert dashboard.exchange_state.pair_status == "waiting_response"
    assert dashboard.exchange_state.opponent_response_state == "waiting"
    assert dashboard.exchange_state.source.name == "Actor 1"
    assert dashboard.exchange_state.target.name == "Actor 2"


@pytest.mark.asyncio
async def test_combat_dashboard_exchange_state_marks_opponent_responded():
    service = CombatSessionService(store=OpponentRespondedCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    dashboard = await service.get_dashboard(1)

    assert dashboard.action_state == "ACTION_LOCKED"
    assert dashboard.exchange_state is not None
    assert dashboard.exchange_state.pair_status == "ready_to_resolve"
    assert dashboard.exchange_state.opponent_response_state == "responded"


@pytest.mark.asyncio
async def test_combat_dashboard_exposes_enemy_commit_timer_state(monkeypatch):
    monkeypatch.setattr("src.backend.features.combat.services.view_service.time.time", lambda: 1_000)
    service = CombatSessionService(store=OpponentDeadlineCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    dashboard = await service.get_dashboard(1)

    assert dashboard.target is not None
    assert dashboard.target.committed is True
    assert dashboard.target.commit_state == "half_time"
    assert dashboard.target.remaining_ms == 25_000
    assert dashboard.target.timeout_total_ms == 60_000
    assert dashboard.enemies[0].commit_state == "half_time"


@pytest.mark.asyncio
async def test_combat_dashboard_marks_empty_queue_only_without_pending_action():
    service = CombatSessionService(store=EmptyTargetCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    dashboard = await service.get_dashboard(1)

    assert dashboard.target is None
    assert dashboard.pending_action_count == 0
    assert dashboard.action_state == "TARGET_QUEUE_EMPTY"
    assert dashboard.exchange_state is not None
    assert dashboard.exchange_state.pair_status == "no_target"


@pytest.mark.asyncio
async def test_combat_dashboard_skips_dead_target_queue_entries():
    service = CombatSessionService(store=DeadFirstTargetCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    dashboard = await service.get_dashboard(1)

    assert dashboard.target is not None
    assert dashboard.target.actor_id == "3"
    exchange = next(action for action in dashboard.available_actions if action.action == "exchange")
    assert exchange.target_id == "3"
    assert dashboard.round_size == 2


@pytest.mark.asyncio
async def test_combat_dashboard_finishes_when_viewer_team_is_dead():
    service = CombatSessionService(store=DeadViewerTeamCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    dashboard = await service.get_dashboard(1)

    assert dashboard.status == "finished"
    assert dashboard.action_state == "FINISHED"
    assert dashboard.winner_team == "team_2"
    assert dashboard.hero.is_dead is True


@pytest.mark.asyncio
async def test_combat_view_endpoint_returns_result_when_viewer_team_is_dead():
    service = CombatSessionService(store=DeadViewerTeamCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    response = await get_combat_view(1, CombatRuntimeOrchestrator(service))

    assert response.payload_type == "CombatResult"
    assert isinstance(response.payload, CombatResultDTO)
    assert response.payload.status == "finished"
    assert response.payload.outcome == "defeat"


@pytest.mark.asyncio
async def test_post_exchange_rejects_dead_target_even_if_queue_is_stale():
    service = CombatSessionService(store=DeadFirstTargetCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    with pytest.raises(HTTPException) as exc_info:
        await register_combat_move(
            1,
            CombatRegisterMoveRequestDTO(action="exchange", target_id="2", feint_id=None),
            CombatRuntimeOrchestrator(service),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "combat_target_unavailable"
    assert exc_info.value.extra["context"]["target_id"] == "2"


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
async def test_post_exchange_rejects_feint_when_concentration_is_too_low():
    store = LowStaminaCombatStore()
    service = CombatSessionService(store=store, system_integrator=FakeCombatSystemIntegrator())

    with pytest.raises(HTTPException) as exc_info:
        await register_combat_move(
            1,
            CombatRegisterMoveRequestDTO(action="exchange", target_id="2", feint_id="true_strike"),
            CombatRuntimeOrchestrator(service),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "combat_feint_unavailable"
    assert exc_info.value.extra["context"]["required_stamina"] == 5
    assert exc_info.value.extra["context"]["current_stamina"] == 4
    assert store.exchange_moves == []
    assert store.returned_feints == [("combat-1", 1, "true_strike", {"hit": 1})]


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
    assert store.started_sessions == []


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
async def test_archived_result_uses_death_return_state_when_death_is_pending() -> None:
    class DeathPendingIntegrator(FakeCombatSystemIntegrator):
        async def resolve_return_state_for_character(self, char_id):
            return CoreDomain.DEATH.value

    service = CombatSessionService(store=FinalizedCombatStore(), system_integrator=DeathPendingIntegrator())

    result = await service.get_archived_result(7, reason="combat_session_finished")

    assert result.primary_action.target_state == CoreDomain.DEATH.value


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
async def test_combat_finalized_return_restores_rift_state() -> None:
    events = FakeEvents()
    sessions = FakeCharacterSessions(
        {
            "state": CoreDomain.COMBAT_RESULT.value,
            "prev_state": CoreDomain.RIFT.value,
            "sessions": {
                "combat_id": None,
                "combat_finalization_id": "combat-1",
                "rift_session_id": "rift-run-1",
                "rift_instance_id": "rift-instance-1",
            },
        }
    )
    integrator = CombatSystemIntegrator(
        actor_commitments=FakeCommitments(),
        character_sessions=sessions,
        events=events,
    )

    returned = await integrator.complete_combat_session_return(7, combat_id="combat-1")

    assert returned == CoreDomain.RIFT.value
    assert sessions.patches[0][1]["$.state"] == CoreDomain.RIFT.value
    assert sessions.patches[0][1]["$.prev_state"] == CoreDomain.EXPLORATION.value
    assert sessions.patches[0][1]["$.sessions.combat_finalization_id"] is None
    assert sessions.patches[0][1]["$.sessions.combat_id"] is None


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
async def test_continue_combat_result_routes_to_death_when_finalization_recorded_death() -> None:
    events = FakeEvents()
    sessions = FakeCharacterSessions(
        {
            "state": CoreDomain.COMBAT_RESULT.value,
            "prev_state": CoreDomain.COMBAT.value,
            "sessions": {
                "combat_id": None,
                "combat_finalization_id": "combat-1",
                "death_run_id": "run-1",
                "death_corpse_id": "corpse-1",
            },
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
    assert response.header.current_state == CoreDomain.DEATH
    assert response.payload.target_state == CoreDomain.DEATH
    assert sessions.patches[0][1]["$.sessions.combat_finalization_id"] is None
    assert sessions.patches[0][1]["$.sessions.combat_id"] is None
    assert sessions.patches[0][1]["$.state"] == CoreDomain.DEATH.value
    assert sessions.patches[0][1]["$.prev_state"] == CoreDomain.COMBAT_RESULT.value


@pytest.mark.asyncio
async def test_continue_combat_result_recovers_latest_finalization_and_clears_stale_combat_id() -> None:
    events = FakeEvents()
    sessions = FakeCharacterSessions(
        {
            "state": CoreDomain.EXPLORATION.value,
            "prev_state": CoreDomain.EXPLORATION.value,
            "sessions": {"combat_id": "combat-1", "combat_finalization_id": None},
        }
    )
    service = CombatSessionService(
        store=LatestFinalizedCombatStore(),
        system_integrator=CombatSystemIntegrator(
            actor_commitments=FakeCommitments(),
            character_sessions=sessions,
            events=events,
        ),
    )

    response = await continue_combat_result(7, CombatRuntimeOrchestrator(service))

    assert response.payload_type == "state_transition"
    assert response.header.current_state == CoreDomain.EXPLORATION
    assert response.payload.combat_id == "combat-1"
    assert sessions.patches[0][1]["$.sessions.combat_id"] is None
    assert sessions.patches[0][1]["$.sessions.combat_finalization_id"] is None


@pytest.mark.asyncio
async def test_continue_combat_result_clears_active_combat_when_latest_finalization_differs() -> None:
    events = FakeEvents()
    sessions = FakeCharacterSessions(
        {
            "state": CoreDomain.COMBAT.value,
            "prev_state": CoreDomain.EXPLORATION.value,
            "sessions": {"combat_id": "combat-2", "combat_finalization_id": None},
        }
    )
    service = CombatSessionService(
        store=LatestFinalizedCombatStore(),
        system_integrator=CombatSystemIntegrator(
            actor_commitments=FakeCommitments(),
            character_sessions=sessions,
            events=events,
        ),
    )

    response = await continue_combat_result(7, CombatRuntimeOrchestrator(service))

    assert response.payload_type == "state_transition"
    assert response.header.current_state == CoreDomain.EXPLORATION
    assert response.payload.combat_id == "combat-1"
    assert sessions.patches[0][1]["$.sessions.combat_id"] is None
    assert sessions.patches[0][1]["$.sessions.combat_finalization_id"] is None
    assert sessions.patches[0][1]["$.state"] == CoreDomain.EXPLORATION.value


@pytest.mark.asyncio
async def test_continue_combat_result_returning_to_rift_clears_rift_active_encounter() -> None:
    rift_runtime = FakeRiftRuntime()
    sessions = FakeCharacterSessions(
        {
            "state": CoreDomain.COMBAT_RESULT.value,
            "prev_state": CoreDomain.RIFT.value,
            "sessions": {
                "combat_id": None,
                "combat_finalization_id": "combat-1",
                "rift_session_id": "rift-run-1",
                "post_combat": {"target_state": "rift", "loot_context": {"rift_session_id": "rift-run-1"}},
            },
        }
    )
    service = CombatSessionService(
        store=LatestFinalizedCombatStore(),
        system_integrator=CombatSystemIntegrator(
            actor_commitments=FakeCommitments(),
            character_sessions=sessions,
            events=FakeEvents(),
            rift_runtime=rift_runtime,
        ),
    )

    response = await continue_combat_result(7, CombatRuntimeOrchestrator(service))

    assert response.payload_type == "state_transition"
    assert response.header.current_state == CoreDomain.RIFT
    assert rift_runtime.applied == [
        {
            "combat_id": "combat-1",
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
async def test_continue_combat_result_is_idempotent_when_combat_refs_are_already_clean() -> None:
    sessions = FakeCharacterSessions(
        {
            "state": CoreDomain.EXPLORATION.value,
            "prev_state": None,
            "sessions": {"combat_id": None, "combat_finalization_id": None},
        }
    )
    service = CombatSessionService(
        store=FakeCombatStore(),
        system_integrator=CombatSystemIntegrator(
            actor_commitments=FakeCommitments(),
            character_sessions=sessions,
            events=FakeEvents(),
        ),
    )

    response = await continue_combat_result(7, CombatRuntimeOrchestrator(service))

    assert response.payload_type == "state_transition"
    assert response.header.current_state == CoreDomain.EXPLORATION
    assert response.payload.target_state == CoreDomain.EXPLORATION
    assert sessions.patches == []


@pytest.mark.asyncio
async def test_combat_archive_stub_returns_result_contract():
    result = await CombatResultArchiveService().get_result_for_character(1, combat_id="combat-1")

    assert result.char_id == 1
    assert result.combat_id == "combat-1"
    assert result.archived is False
    assert result.metadata["source"] == "combat_archive_stub"
    assert result.primary_action.action == "navigate"
    assert result.primary_action.target_state == "exploration"
