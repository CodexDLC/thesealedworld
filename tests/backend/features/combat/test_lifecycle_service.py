import pytest

from src.backend.features.combat.integrations import CombatSystemIntegrator
from src.backend.features.combat.orchestrators import CombatCreationOrchestrator
from src.backend.features.combat.services.lifecycle_service import CombatLifecycleService


class FakeEvents:
    def __init__(self):
        self.published = []
        self.requested = []

    async def request(self, event_type, data, timeout=30.0, correlation_id=None):
        self.requested.append((event_type, data, timeout, correlation_id))
        assert event_type == "character.combat_commitments_requested"
        player_ids = _decode_json_list(data["player_ids"])
        monster_ids = _decode_json_list(data["monster_ids"])
        return {
            "status": "ok",
            "commitments": {
                **{f"player:{pid}": f"actor:combat-test:player:{pid}" for pid in player_ids},
                **{f"monster:{mid}": f"actor:combat-test:monster:{mid}" for mid in monster_ids},
            },
        }

    async def publish(self, event_type, data, correlation_id=None):
        self.published.append((event_type, data, correlation_id))
        return "1-0"


class FakeActorCommitments:
    @staticmethod
    def source_ref(actor_type, source_id):
        return f"{actor_type}:{source_id}"

    async def get_snapshots_batch(self, keys):
        snapshots = {}
        for key in keys:
            _prefix, _scope_id, kind, actor_id = key.split(":", 3)
            snapshots[key] = _player_snapshot(int(actor_id)) if kind == "player" else _monster_snapshot(actor_id)
        return snapshots


class FakeCharacterSessions:
    def __init__(self):
        self.combat = {}
        self.states = {}

    async def set_combat_session(self, char_id, combat_id):
        self.combat[char_id] = combat_id

    async def set_state(self, char_id, state):
        self.states[char_id] = state


class FakeStore:
    def __init__(self):
        self.created = None

    async def create_session_batch(self, session_id, data, *, ttl=3600):
        self.created = (session_id, data, ttl)


class FakeLootPreorder:
    def __init__(self):
        self.calls = []

    async def enqueue(self, **kwargs):
        self.calls.append(kwargs)


def _decode_json_list(value):
    import json

    return json.loads(value) if isinstance(value, str) else value


def _orchestrator(store, events=None, sessions=None, loot_preorder=None):
    return CombatCreationOrchestrator(
        lifecycle=CombatLifecycleService(store=store),
        integrator=CombatSystemIntegrator(
            actor_commitments=FakeActorCommitments(),
            character_sessions=sessions or FakeCharacterSessions(),
            events=events or FakeEvents(),
        ),
        loot_preorder=loot_preorder,
    )


def _player_snapshot(char_id):
    return {
        "meta": {
            "actor_type": "player",
            "actor_id": char_id,
            "name": f"Hero {char_id}",
            "avatar_url": "/static/images/avatars/rook7.png",
            "gender": "male",
        },
        "combat": {
            "math_model": {"attributes": {"strength": {"base": 5}}, "modifiers": {}},
            "loadout": {"known_feints": ["quick_cut"]},
            "skills": {"swords": 1.0},
        },
        "status": {"hp": {"cur": 64, "max": 64}, "energy": {"cur": 26, "max": 26}},
        "source": {"character_id": char_id},
    }


def _monster_snapshot(monster_id):
    return {
        "meta": {"actor_type": "monster", "actor_id": monster_id, "name": "Rat"},
        "combat": {
            "math_model": {"attributes": {"agility": {"base": 4}}, "modifiers": {}},
            "loadout": {"known_feints": ["bite"]},
            "skills": {"natural_weapon": 1.0},
        },
        "runtime": {"vitals": {"hp": {"cur": 20}, "energy": {"cur": 10}}},
        "status": {"hp": {"cur": 20}, "energy": {"cur": 10}},
        "source": {"monster_id": monster_id, "template_id": "rat"},
    }


@pytest.mark.asyncio
async def test_lifecycle_creates_arena_pvp_session():
    store = FakeStore()
    events = FakeEvents()
    sessions = FakeCharacterSessions()
    service = _orchestrator(store, events=events, sessions=sessions)

    ready = await service.create_from_request(
        {
            "source": "arena",
            "arena_session_id": "arena:1",
            "battle_type": "pvp",
            "requested_by": 1,
            "participants": {"team_1": [1], "team_2": [2]},
        }
    )

    session_id, data, ttl = store.created
    assert ready["combat_id"] == session_id
    assert set(data.actors) == {"1", "2"}
    assert data.actors["1"]["meta"]["hp"] == 64
    assert data.actors["1"]["meta"]["max_hp"] == 64
    assert data.actors["1"]["meta"]["en"] == 26
    assert data.actors["1"]["meta"]["max_en"] == 26
    assert data.targets["1"] == ["2"]
    assert sessions.combat == {}
    assert sessions.states == {}
    assert events.published[0][0] == "combat.session_ready"


@pytest.mark.asyncio
async def test_lifecycle_uses_provided_arena_commitments_without_requesting_character_data():
    store = FakeStore()
    events = FakeEvents()
    service = _orchestrator(store, events=events)

    await service.create_from_request(
        {
            "source": "arena",
            "arena_session_id": "arena:prepared",
            "combat_id": "arena-prepared",
            "battle_type": "pvp",
            "requested_by": 1,
            "participants": {"team_1": [1], "team_2": [2]},
            "commitments": {
                "player:1": "actor:arena-prepared:player:1",
                "player:2": "actor:arena-prepared:player:2",
            },
        }
    )

    _, data, _ = store.created
    assert set(data.actors) == {"1", "2"}
    assert data.actors["1"]["meta"]["name"] == "Hero 1"
    assert events.requested == []


@pytest.mark.asyncio
async def test_lifecycle_does_not_link_players_during_session_creation():
    store = FakeStore()
    sessions = FakeCharacterSessions()
    service = _orchestrator(store, sessions=sessions)

    await service.create_from_request(
        {
            "source": "arena",
            "arena_session_id": "arena:prepared",
            "battle_type": "pvp",
            "requested_by": 1,
            "participants": {"team_1": [1], "team_2": [2]},
        }
    )

    assert store.created is not None
    assert sessions.combat == {}
    assert sessions.states == {}


@pytest.mark.asyncio
async def test_lifecycle_creates_shadow_clone():
    store = FakeStore()
    sessions = FakeCharacterSessions()
    service = _orchestrator(store, sessions=sessions)

    await service.create_from_request(
        {
            "source": "arena",
            "battle_type": "shadow",
            "requested_by": 7,
            "participants": {"team_1": [7], "team_2": []},
            "metadata": {"awaiting_player_choice": True},
            "ttl": 900,
        }
    )

    _, data, ttl = store.created
    assert set(data.actors) == {"7", "-7"}
    assert data.actors["-7"]["meta"]["is_ai"] is True
    assert data.actors["-7"]["meta"]["type"] == "shadow"
    assert "shadow" in data.actors["-7"]["meta"]["tags"]
    assert data.actors["-7"]["meta"]["name"].startswith("Shadow ")
    assert data.actors["-7"]["meta"]["avatar_url"] == "/static/images/avatars/rook7.png"
    assert data.actors["-7"]["meta"]["source_ref"] == "player:7"
    assert data.actors["-7"]["meta"]["hp"] == 64
    assert data.actors["-7"]["meta"]["max_hp"] == 64
    assert ttl == 900
    assert sessions.combat == {}


@pytest.mark.asyncio
async def test_lifecycle_clones_repeated_monster_snapshots():
    store = FakeStore()
    service = _orchestrator(store)
    monster_id = "00000000-0000-0000-0000-000000000001"

    await service.create_from_request(
        {
            "source": "arena",
            "battle_type": "pve",
            "requested_by": 1,
            "participants": {"team_1": [1], "team_2": [monster_id, monster_id]},
        }
    )

    _, data, _ = store.created
    assert set(data.actors) == {"1", f"{monster_id}_1", f"{monster_id}_2"}
    assert data.actors[f"{monster_id}_1"]["meta"]["type"] == "monster"
    assert data.actors[f"{monster_id}_2"]["meta"]["template_id"] == monster_id


@pytest.mark.asyncio
async def test_lifecycle_preorders_hidden_loot_for_non_arena_monsters():
    store = FakeStore()
    loot_preorder = FakeLootPreorder()
    service = _orchestrator(store, loot_preorder=loot_preorder)
    monster_id = "00000000-0000-0000-0000-000000000002"

    await service.create_from_request(
        {
            "source": "exploration",
            "battle_type": "pve",
            "location_id": "forest",
            "requested_by": 1,
            "participants": {"team_1": [1], "team_2": [monster_id]},
        }
    )

    assert len(loot_preorder.calls) == 1
    call = loot_preorder.calls[0]
    assert call["battle_type"] == "pve"
    assert call["location_id"] == "forest"
    assert set(call["actors"]) == {"1", f"{monster_id}_1"}
