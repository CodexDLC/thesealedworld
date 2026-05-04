from types import SimpleNamespace

import pytest

from src.backend.features.arena.dto.session import ArenaCombatRequestDTO
from src.backend.features.arena import events as arena_events


class FakeArenaStore:
    match = ArenaCombatRequestDTO(
        arena_session_id="arena:ready",
        mode="one_vs_one",
        battle_type="pvp",
        requested_by=1,
        participants={"team_1": [1], "team_2": [2]},
    )
    updated = None

    def __init__(self, redis):
        self.redis = redis

    async def get_match(self, arena_session_id):
        return self.match if arena_session_id == self.match.arena_session_id else None

    async def update_match(self, match):
        self.__class__.updated = match


@pytest.mark.asyncio
async def test_combat_ready_marks_arena_match_ready(monkeypatch):
    monkeypatch.setattr(arena_events, "ArenaSessionStore", FakeArenaStore)
    arena_events.bind(SimpleNamespace(state=SimpleNamespace(redis=object())))

    await arena_events.on_combat_session_ready(
        {"source": "arena", "arena_session_id": "arena:ready", "combat_id": "combat-1"}
    )

    assert FakeArenaStore.updated.status == "ready"
    assert FakeArenaStore.updated.combat_id == "combat-1"


@pytest.mark.asyncio
async def test_combat_failed_marks_arena_match_failed(monkeypatch):
    FakeArenaStore.match.status = "pending"
    FakeArenaStore.match.combat_id = None
    FakeArenaStore.updated = None
    monkeypatch.setattr(arena_events, "ArenaSessionStore", FakeArenaStore)
    arena_events.bind(SimpleNamespace(state=SimpleNamespace(redis=object())))

    await arena_events.on_combat_session_failed(
        {"source": "arena", "arena_session_id": "arena:ready", "error": "boom"}
    )

    assert FakeArenaStore.updated.status == "failed"
    assert FakeArenaStore.updated.metadata["combat_error"] == "boom"
