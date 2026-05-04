import pytest

from src.backend.features.combat.integrations import CombatSystemIntegrator
from src.backend.features.combat.orchestrators import CombatCreationOrchestrator
from src.backend.features.combat.services.lifecycle_service import CombatLifecycleService


class FakeEvents:
    def __init__(self):
        self.published = []

    async def request(self, event_type, data, timeout=30.0, correlation_id=None):
        assert event_type == "actor_state.snapshots_requested"
        session_id = data["session_id"]
        player_ids = _decode_json_list(data["player_ids"])
        monster_ids = _decode_json_list(data["monster_ids"])
        return {
            "status": "ok",
            "snapshot_keys": {
                **{f"{session_id}:player:{pid}": f"snapshot:player:{pid}" for pid in player_ids},
                **{f"{session_id}:monster:{mid}": f"snapshot:monster:{mid}" for mid in monster_ids},
            },
        }

    async def publish(self, event_type, data, correlation_id=None):
        self.published.append((event_type, data, correlation_id))
        return "1-0"


class FakeActorSnapshots:
    async def get_snapshots_batch(self, keys):
        snapshots = {}
        for key in keys:
            kind, actor_id = key.split(":")[-2:]
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


def _decode_json_list(value):
    import json

    return json.loads(value) if isinstance(value, str) else value


def _orchestrator(store, events=None, sessions=None):
    return CombatCreationOrchestrator(
        lifecycle=CombatLifecycleService(store=store),
        integrator=CombatSystemIntegrator(
            actor_snapshots=FakeActorSnapshots(),
            character_sessions=sessions or FakeCharacterSessions(),
            events=events or FakeEvents(),
        ),
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
        "status": {"hp": {"cur": 80}, "energy": {"cur": 30}},
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
    assert data.targets["1"] == ["2"]
    assert sessions.combat[1] == session_id
    assert events.published[0][0] == "combat.session_ready"


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
    assert data.actors["-7"]["meta"]["name"].startswith("Shadow ")
    assert data.actors["-7"]["meta"]["avatar_url"] == "/static/images/avatars/rook7.png"
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
