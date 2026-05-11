import json

import pytest

from src.backend.features.combat.dto.session import SessionDataDTO
from src.backend.infrastructure.combat.managers.session import CombatSessionManager


class JsonProxy:
    def __init__(self, client):
        self.client = client

    async def get(self, key, path="$"):
        value = self.client.json_store.get(key)
        if path == "$":
            return [value] if value is not None else None
        return [value.get(path.removeprefix("$."))] if isinstance(value, dict) else None


class FakePipeline:
    def __init__(self, client):
        self.client = client
        self.commands = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    def json(self):
        return self

    def hset(self, key, mapping=None, **kwargs):
        self.commands.append(("hset", key, mapping or kwargs))

    def expire(self, key, ttl):
        self.commands.append(("expire", key, ttl))

    def set(self, key, path, value):
        self.commands.append(("json_set", key, path, value))

    def get(self, key, path="$"):
        self.commands.append(("json_get", key, path))

    def lrange(self, key, start, stop):
        self.commands.append(("lrange", key, start, stop))

    def delete(self, key):
        self.commands.append(("delete", key, None))

    async def execute(self, raise_on_error=True):
        results = []
        for command in self.commands:
            name, key, *payload = command
            if name == "hset":
                self.client.hash_store.setdefault(key, {}).update(payload[0])
                results.append(True)
            elif name == "expire":
                self.client.ttls[key] = payload[0]
                results.append(True)
            elif name == "json_set":
                _, value = payload
                self.client.json_store[key] = value
                results.append(True)
            elif name == "json_get":
                path = payload[0]
                value = self.client.json_store.get(key)
                if path == "$":
                    results.append([value] if value is not None else None)
                else:
                    results.append(None)
            elif name == "lrange":
                start, stop = payload
                values = self.client.lists.get(key, [])
                end = None if stop == -1 else stop + 1
                results.append(values[start:end])
            elif name == "delete":
                self.client.json_store.pop(key, None)
                self.client.hash_store.pop(key, None)
                self.client.lists.pop(key, None)
                results.append(True)
        return results


class FakeRedisClient:
    def __init__(self):
        self.hash_store = {}
        self.json_store = {}
        self.lists = {}
        self.ttls = {}

    def pipeline(self, transaction=False):
        return FakePipeline(self)

    async def hgetall(self, key):
        return self.hash_store.get(key, {})

    async def hset(self, key, mapping=None, **kwargs):
        self.hash_store.setdefault(key, {}).update(mapping or kwargs)

    async def rpush(self, key, *values):
        self.lists.setdefault(key, []).extend(values)

    async def lrange(self, key, start, stop):
        values = self.lists.get(key, [])
        end = None if stop == -1 else stop + 1
        return values[start:end]

    async def eval(self, script, numkeys, *args):
        if "local actions = cjson.decode(ARGV[1])" not in script:
            raise NotImplementedError(script)

        queue_key = args[0]
        actions_json = json.loads(args[1])
        fallback_deletes = json.loads(args[2])
        ttl = int(args[3])
        session_id = args[4]
        pushed = 0

        def moves_key(actor_id):
            return f"combat:rbc:{session_id}:actor:{actor_id}:moves"

        def move_exists(move):
            doc = self.json_store.get(moves_key(move["char_id"]), {})
            return move["move_id"] in doc.get(move["strategy"], {})

        def delete_move(move):
            key = moves_key(move["char_id"])
            doc = self.json_store.get(key, {})
            doc.get(move["strategy"], {}).pop(move["move_id"], None)
            self.ttls[key] = ttl

        for action_json in actions_json:
            action = json.loads(action_json)
            valid = bool(action.get("move")) and move_exists(action["move"])
            partner_move = action.get("partner_move")
            if valid and partner_move is not None:
                valid = move_exists(partner_move)

            if valid:
                self.lists.setdefault(queue_key, []).append(action_json)
                delete_move(action["move"])
                if partner_move is not None:
                    delete_move(partner_move)
                pushed += 1

        if not actions_json:
            for item in fallback_deletes:
                delete_move(item)

        return pushed


class FakeRedisService:
    def __init__(self):
        self.redis_client = FakeRedisClient()
        self.json_module = JsonProxy(self.redis_client)


@pytest.mark.asyncio
async def test_create_session_batch_writes_rbc_shape():
    redis = FakeRedisService()
    store = CombatSessionManager(redis)

    await store.create_session_batch(
        "c1",
        SessionDataDTO(
            meta={"active": 1, "teams": '{"blue":["1"],"red":["-1"]}'},
            actors={"1": {"meta": {"id": "1"}}, "-1": {"meta": {"id": "-1"}}},
            targets={"1": ["-1"], "-1": ["1"]},
        ),
        ttl=123,
    )

    assert redis.redis_client.hash_store["combat:rbc:c1:meta"]["active"] == 1
    assert redis.redis_client.json_store["combat:rbc:c1:targets"] == {"1": ["-1"], "-1": ["1"]}
    assert redis.redis_client.json_store["combat:rbc:c1:actor:1:moves"]["exchange"] == {}
    assert redis.redis_client.ttls["combat:rbc:c1:actor:-1"] == 123


@pytest.mark.asyncio
async def test_logs_round_trip():
    redis = FakeRedisService()
    store = CombatSessionManager(redis)

    await store.append_log("c1", {"text": "started"})

    assert await store.get_logs("c1") == ['{"text": "started"}']
    assert await store.get_logs_by_turn("c1") == {"0": ['{"text": "started"}']}


@pytest.mark.asyncio
async def test_commit_battle_results_groups_logs_by_global_turn():
    redis = FakeRedisService()
    store = CombatSessionManager(redis)

    await store.commit_battle_results(
        "c1",
        {},
        [{"global_turn": 1, "text": "first"}, {"global_turn": 1, "text": "second"}],
        0,
    )
    await store.commit_battle_results("c1", {}, [{"global_turn": 2, "text": "third"}], 0)

    assert await store.get_logs_by_turn("c1") == {
        "1": ['{"global_turn": 1, "text": "first"}', '{"global_turn": 1, "text": "second"}'],
        "2": ['{"global_turn": 2, "text": "third"}'],
    }
    assert await store.get_logs("c1") == [
        '{"global_turn": 1, "text": "first"}',
        '{"global_turn": 1, "text": "second"}',
        '{"global_turn": 2, "text": "third"}',
    ]


@pytest.mark.asyncio
async def test_commit_battle_results_appends_logs_to_existing_global_turn():
    redis = FakeRedisService()
    store = CombatSessionManager(redis)

    await store.commit_battle_results("c1", {}, [{"global_turn": 1, "text": "first"}], 0)
    await store.commit_battle_results("c1", {}, [{"global_turn": 1, "text": "second"}], 0)

    assert await store.get_logs_by_turn("c1") == {
        "1": ['{"global_turn": 1, "text": "first"}', '{"global_turn": 1, "text": "second"}']
    }


@pytest.mark.asyncio
async def test_commit_battle_results_persists_meta_updates():
    redis = FakeRedisService()
    store = CombatSessionManager(redis)

    await store.commit_battle_results("c1", {}, [], 0, meta_update={"step_counter": 3})

    assert redis.redis_client.hash_store["combat:rbc:c1:meta"]["step_counter"] == 3


@pytest.mark.asyncio
async def test_load_full_context_data_preserves_actor_feints_from_meta():
    redis = FakeRedisService()
    store = CombatSessionManager(redis)
    redis.redis_client.json_store["combat:rbc:c1:actor:1"] = {
        "meta": {
            "id": "1",
            "hp": 10,
            "max_hp": 10,
            "tokens": {"hit": 2},
            "feints": {"arsenal": ["true_strike"], "hand": {"true_strike": {"hit": 2}}, "pinned": "true_strike"},
        },
        "raw": {},
        "loadout": {},
        "statuses": {"abilities": [], "effects": []},
    }
    redis.redis_client.json_store["combat:rbc:c1:actor:1:moves"] = {"exchange": {}}

    data = await store.load_full_context_data("c1", ["1"])

    assert data["1"]["state"]["feints"] == {
        "arsenal": ["true_strike"],
        "hand": {"true_strike": {"hit": 2}},
        "pinned": "true_strike",
    }


def test_exchange_registration_lua_prefers_string_target_ids():
    source = CombatSessionManager.register_exchange_move_atomic.__code__.co_consts
    script = next(value for value in source if isinstance(value, str) and "JSON.ARRINDEX" in value)

    assert "ARGV[2]) or ARGV[2]" not in script
    assert """local actor_path = '$["' .. ARGV[1] .. '"]'""" in script
    assert "JSON.ARRINDEX', KEYS[1], actor_path, cjson.encode(ARGV[2])" in script
    assert "tonumber(ARGV[2])" in script


def test_targets_json_paths_use_bracket_notation_for_numeric_actor_ids():
    assert CombatSessionManager._json_member_path(5) == '$["5"]'
    assert CombatSessionManager._json_member_path("-5") == '$["-5"]'


@pytest.mark.asyncio
async def test_transfer_intents_to_actions_skips_stale_duplicate_transfer():
    redis = FakeRedisService()
    store = CombatSessionManager(redis)
    redis.redis_client.json_store["combat:rbc:c1:actor:1:moves"] = {
        "exchange": {"m1": {"move_id": "m1", "strategy": "exchange", "char_id": 1}}
    }
    redis.redis_client.json_store["combat:rbc:c1:actor:-1:moves"] = {
        "exchange": {"m2": {"move_id": "m2", "strategy": "exchange", "char_id": -1}}
    }
    action = {
        "action_type": "exchange",
        "move": {"move_id": "m1", "strategy": "exchange", "char_id": 1},
        "partner_move": {"move_id": "m2", "strategy": "exchange", "char_id": -1},
        "is_forced": False,
    }
    action_json = json.dumps(action)
    deletes = [
        {"char_id": 1, "strategy": "exchange", "move_id": "m1"},
        {"char_id": -1, "strategy": "exchange", "move_id": "m2"},
    ]

    await store.transfer_intents_to_actions("c1", [action_json], deletes)
    await store.transfer_intents_to_actions("c1", [action_json], deletes)

    assert redis.redis_client.lists["combat:rbc:c1:q:actions"] == [action_json]
    assert redis.redis_client.json_store["combat:rbc:c1:actor:1:moves"]["exchange"] == {}
    assert redis.redis_client.json_store["combat:rbc:c1:actor:-1:moves"]["exchange"] == {}


@pytest.mark.asyncio
async def test_transfer_intents_to_actions_accepts_null_partner_move():
    redis = FakeRedisService()
    store = CombatSessionManager(redis)
    redis.redis_client.json_store["combat:rbc:c1:actor:1:moves"] = {
        "exchange": {"m1": {"move_id": "m1", "strategy": "exchange", "char_id": 1}}
    }
    action = {
        "action_type": "exchange",
        "move": {"move_id": "m1", "strategy": "exchange", "char_id": 1},
        "partner_move": None,
        "is_forced": True,
    }
    action_json = json.dumps(action)

    await store.transfer_intents_to_actions(
        "c1",
        [action_json],
        [{"char_id": 1, "strategy": "exchange", "move_id": "m1"}],
    )

    assert redis.redis_client.lists["combat:rbc:c1:q:actions"] == [action_json]
    assert redis.redis_client.json_store["combat:rbc:c1:actor:1:moves"]["exchange"] == {}
