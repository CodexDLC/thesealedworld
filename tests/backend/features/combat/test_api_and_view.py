import json

import pytest

from src.backend.features.combat.integrations import CombatSystemIntegrator
from src.backend.features.combat.services.result_archive_service import CombatResultArchiveService
from src.backend.features.combat.services.session_service import CombatSessionService
from src.shared.enums import CoreDomain


class FakeCombatStore:
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
                },
                "loadout": {
                    "belt": [
                        {
                            "item_id": "potion-1",
                            "name": "Small Potion",
                            "belt_slot": "slot_1",
                            "item_type": "consumable",
                        }
                    ]
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
        return [json.dumps({"text": "started"})]


class MissingCombatStore(FakeCombatStore):
    async def get_meta(self, session_id):
        return None


class FakeCombatSystemIntegrator:
    def __init__(self):
        self.recovered = []

    async def resolve_combat_session_for_character(self, char_id):
        return "combat-1"

    async def recover_missing_combat_session(self, char_id, *, combat_id=None):
        self.recovered.append((char_id, combat_id))
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
async def test_combat_dashboard_derives_session_display_state():
    service = CombatSessionService(store=FakeCombatStore(), system_integrator=FakeCombatSystemIntegrator())

    dashboard = await service.get_dashboard(1)

    assert dashboard.phase == "ACTION_READY"
    assert dashboard.personal_turn_number == 2
    assert dashboard.round_size == 2
    assert dashboard.target_queue_size == 1
    assert dashboard.hero.quick_items[0]["item_id"] == "potion-1"


@pytest.mark.asyncio
async def test_missing_live_combat_session_recovers_stale_ac_before_fallback():
    integrator = FakeCombatSystemIntegrator()
    service = CombatSessionService(store=MissingCombatStore(), system_integrator=integrator)

    with pytest.raises(ValueError, match="Combat session not found: combat-1"):
        await service.get_dashboard(1)

    assert integrator.recovered == [(1, "combat-1")]


@pytest.mark.asyncio
async def test_combat_recovery_clears_ac_combat_id_and_restores_previous_state():
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
                "$.prev_state": CoreDomain.COMBAT.value,
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
async def test_combat_archive_stub_returns_result_contract():
    result = await CombatResultArchiveService().get_result_for_character(1, combat_id="combat-1")

    assert result.char_id == 1
    assert result.combat_id == "combat-1"
    assert result.archived is False
    assert result.metadata["source"] == "combat_archive_stub"
    assert result.primary_action.action == "navigate"
    assert result.primary_action.target_state == "exploration"
