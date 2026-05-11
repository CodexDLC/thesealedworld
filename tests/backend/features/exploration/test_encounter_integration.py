from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.backend.features.exploration.integrations import (
    COMBAT_SESSION_REQUESTED,
    MONSTER_GROUP_PREPARE_REQUESTED,
    EncounterIntegration,
)


class FakeCharacterSessions:
    def __init__(self, skills: dict | None = None) -> None:
        self.skills = skills or {}
        self.applied: tuple[int, dict[str, float]] | None = None
        self.locations: list[tuple[int, str, str | None]] = []
        self.combat_sessions: list[tuple[int, str]] = []
        self.encounter_id: str | None = None

    async def get_skills(self, char_id: int) -> dict:
        return self.skills

    async def get_section(self, char_id: int, section: str):
        if section == "sessions":
            return {"encounter_id": self.encounter_id}
        return None

    async def apply_skill_progress(self, char_id: int, rewards: dict[str, float]) -> None:
        self.applied = (char_id, rewards)

    async def set_location(self, char_id: int, loc_id: str, *, prev: str | None = None) -> None:
        self.locations.append((char_id, loc_id, prev))

    async def set_combat_session(self, char_id: int, combat_id: str) -> None:
        self.combat_sessions.append((char_id, combat_id))

    async def set_encounter_session(self, char_id: int, encounter_id: str) -> None:
        self.encounter_id = encounter_id

    async def clear_encounter_session(self, char_id: int) -> None:
        self.encounter_id = None


class FakeWorldStore:
    def __init__(self) -> None:
        self.locations = {
            "52_52": {
                "flags": {"threat_tier": 1},
                "anchor_influence": {"tags": ["mana_leak"]},
            }
        }
        self.moves: list[tuple[str, int | str]] = []

    async def get_location(self, loc_id: str) -> dict | None:
        return self.locations.get(loc_id)

    async def location_exists(self, loc_id: str) -> bool:
        return loc_id in self.locations

    async def remove_player(self, loc_id: str, char_id: int) -> None:
        self.moves.append((f"remove:{loc_id}", char_id))

    async def add_player(self, loc_id: str, char_id: int) -> None:
        self.moves.append((f"add:{loc_id}", char_id))


class FakeRedis:
    def __init__(self) -> None:
        self.json_module = AsyncMock()
        self.string = AsyncMock()


class FakeEvents:
    def __init__(self) -> None:
        self.requests: list[tuple[str, dict, float, str | None]] = []

    async def request(self, event_name: str, payload: dict, *, timeout: float, correlation_id: str | None = None):
        self.requests.append((event_name, payload, timeout, correlation_id))
        if event_name == MONSTER_GROUP_PREPARE_REQUESTED:
            scope_id = payload.get("scope_id") or "monster_group:test"
            return {
                "status": "ok",
                "payload": {
                    "group_id": scope_id,
                    "group_key": f"game:monster:group:{scope_id}",
                    "clan_id": "clan-1",
                    "family_id": "wolf_pack",
                    "loc_id": payload["loc_id"],
                    "zone_id": "zone-1",
                    "biome_id": "wasteland",
                    "tier": 1,
                    "danger": 0.25,
                    "target_budget": float(payload["budget"]),
                    "adjusted_budget": float(payload["budget"]),
                    "total_power": 110,
                    "monster_ids": ["m1", "m2"],
                    "actor_commitments": {
                        "monster:m1": f"{scope_id}:monster:m1",
                        "monster:m2": f"{scope_id}:monster:m2",
                    },
                    "previews": [],
                    "reused_existing_clan": True,
                    "context_hash": "ctx",
                    "unique_hash": "unique",
                    "tags": ["wolf"],
                },
            }
        return {"status": "ok", "event": event_name}


@pytest.mark.unit
async def test_get_ac_skill_snapshot_normalizes_encounter_skills() -> None:
    sessions = FakeCharacterSessions(
        {
            "skill_scouting": {"xp": 0.42, "unlocked": True},
            "skill_pathfinder": 0.31,
            "skill_hunting": {"total_xp": "0.27"},
            "skill_taming": {"xp": 0.9, "unlocked": False},
            "survival": 99,
        }
    )

    snapshot = await EncounterIntegration(character_sessions=sessions).get_ac_skill_snapshot(7)  # type: ignore[arg-type]

    assert snapshot.as_dict() == {
        "skill_scouting": 0.42,
        "skill_pathfinder": 0.31,
        "skill_hunting": 0.27,
        "skill_taming": 0.0,
    }
    assert snapshot.value("survival") == 0.0


@pytest.mark.unit
async def test_apply_skill_progress_delegates_clean_rewards_to_ac_session() -> None:
    sessions = FakeCharacterSessions()
    integration = EncounterIntegration(character_sessions=sessions)  # type: ignore[arg-type]

    await integration.apply_skill_progress(7, {"skill_scouting": 0.001, "free_xp": 1.0, "skill_hunting": 0})

    assert sessions.applied == (7, {"skill_scouting": 0.001})


@pytest.mark.unit
async def test_location_context_and_move_actor_use_world_store_and_ac_session() -> None:
    sessions = FakeCharacterSessions()
    world = FakeWorldStore()
    integration = EncounterIntegration(character_sessions=sessions, world_store=world)  # type: ignore[arg-type]

    context = await integration.get_location_context("52_52")
    moved = await integration.move_actor(7, "52_51", "52_52")

    assert context is not None
    assert context.flags == {"threat_tier": 1}
    assert context.anchor_influence == {"tags": ["mana_leak"]}
    assert moved is True
    assert world.moves == [("remove:52_51", 7), ("add:52_52", 7)]
    assert sessions.locations == [(7, "52_52", "52_51")]


@pytest.mark.unit
async def test_cached_monsters_use_redis_json_payload() -> None:
    redis = FakeRedis()
    redis.json_module.get.return_value = [{"monster_ids": ["m1"]}]
    integration = EncounterIntegration(character_sessions=FakeCharacterSessions(), redis=redis)  # type: ignore[arg-type]

    cached = await integration.get_cached_encounter_monsters("encounter:monsters:1")
    await integration.set_cached_encounter_monsters("encounter:monsters:1", {"monster_ids": ["m2"]}, ttl_seconds=60)

    assert cached == {"monster_ids": ["m1"]}
    redis.json_module.set.assert_awaited_once_with("encounter:monsters:1", "$", {"monster_ids": ["m2"]})
    redis.string.expire.assert_awaited_once_with("encounter:monsters:1", 60)


@pytest.mark.unit
async def test_encounter_session_lifecycle_uses_ac_ref_and_game_encounter_redis_json(
    fake_redis_service,
    fake_redis_client,
) -> None:
    sessions = FakeCharacterSessions()
    integration = EncounterIntegration(character_sessions=sessions, redis=fake_redis_service)  # type: ignore[arg-type]

    await integration.attach_encounter_session(7, "enc-1")
    active_id = await integration.get_active_encounter_id(7)
    created = await integration.create_encounter_session(
        "enc-1",
        {"char_id": 7, "payload": {"id": "enc-1", "title": "Threat"}},
        ttl_seconds=90,
    )
    loaded = await integration.get_encounter_session("enc-1")
    loaded_payload_title = loaded["payload"]["title"] if loaded is not None else None
    await integration.patch_encounter_session("enc-1", {"status": "pending", "$.payload.title": "Updated"})
    patched = await integration.get_encounter_session("enc-1")
    ttl = fake_redis_client.ttls["game:encounter:enc-1"]
    await integration.clear_encounter_session("enc-1")
    await integration.detach_encounter_session(7)

    assert active_id == "enc-1"
    assert created == {
        "char_id": 7,
        "payload": {"id": "enc-1", "title": "Threat"},
        "encounter_id": "enc-1",
    }
    assert loaded_payload_title == "Threat"
    assert patched is not None
    assert patched["status"] == "pending"
    assert patched["payload"]["title"] == "Updated"
    assert ttl == 90
    assert sessions.encounter_id is None
    assert "game:encounter:enc-1" not in fake_redis_client.store


@pytest.mark.unit
async def test_stream_requests_are_semantic_boundaries() -> None:
    events = FakeEvents()
    sessions = FakeCharacterSessions()
    integration = EncounterIntegration(character_sessions=sessions, events=events)  # type: ignore[arg-type]

    monster_group = await integration.prepare_monster_group(
        "45_45",
        120,
        preferred_family_id="wolf_pack",
        force_single_family=True,
        scope_id="encounter:abc123",
        ttl=300,
        correlation_id="corr-1",
    )
    combat_response = await integration.request_combat_session({"combat_id": "c2"}, correlation_id="corr-2")
    await integration.attach_combat_session(7, "combat-1")

    assert monster_group.group_id == "encounter:abc123"
    assert monster_group.group_key == "game:monster:group:encounter:abc123"
    assert monster_group.family_id == "wolf_pack"
    assert monster_group.monster_ids == ["m1", "m2"]
    assert monster_group.actor_commitments == {
        "monster:m1": "encounter:abc123:monster:m1",
        "monster:m2": "encounter:abc123:monster:m2",
    }
    assert combat_response == {"status": "ok", "event": COMBAT_SESSION_REQUESTED}
    assert events.requests == [
        (
            MONSTER_GROUP_PREPARE_REQUESTED,
            {
                "loc_id": "45_45",
                "budget": "120",
                "force_single_family": "true",
                "ttl": "300",
                "preferred_family_id": "wolf_pack",
                "scope_id": "encounter:abc123",
            },
            10.0,
            "corr-1",
        ),
        (COMBAT_SESSION_REQUESTED, {"combat_id": "c2"}, 30.0, "corr-2"),
    ]
    assert sessions.combat_sessions == [(7, "combat-1")]
