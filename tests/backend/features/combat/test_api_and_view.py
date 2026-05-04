import json

import pytest

from src.backend.features.combat.services.session_service import CombatSessionService


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
        actors = {str(actor_id): {"meta": {"id": str(actor_id)}} for actor_id in actor_ids}
        actors["1"]["meta"]["avatar_url"] = "/static/images/avatars/rook7.png"
        return actors

    async def get_targets(self, session_id):
        return {"1": ["2"], "2": ["1"]}

    async def get_moves_batch(self, session_id, actor_ids):
        return {"1": {"exchange": {}}}

    async def get_logs(self, session_id, *, start=0, stop=-1):
        return [json.dumps({"text": "started"})]


class FakeCharacterSessions:
    async def get_session(self, char_id):
        return {"sessions": {"combat_id": "combat-1"}}


@pytest.mark.asyncio
async def test_combat_session_service_returns_snapshot():
    service = CombatSessionService(store=FakeCombatStore(), character_sessions=FakeCharacterSessions())

    snapshot = await service.get_snapshot(1)

    assert snapshot["session_id"] == "combat-1"
    assert snapshot["meta"]["teams"] == {"team_1": ["1"], "team_2": ["2"]}
    assert snapshot["targets"]["1"] == ["2"]


@pytest.mark.asyncio
async def test_combat_session_service_returns_logs():
    service = CombatSessionService(store=FakeCombatStore(), character_sessions=FakeCharacterSessions())

    logs = await service.get_logs(1)

    assert [entry.text for entry in logs.entries] == ["started"]


@pytest.mark.asyncio
async def test_combat_dashboard_exposes_actor_avatar_url():
    service = CombatSessionService(store=FakeCombatStore(), character_sessions=FakeCharacterSessions())

    dashboard = await service.get_dashboard(1)

    assert dashboard.hero.avatar_url == "/static/images/avatars/rook7.png"
