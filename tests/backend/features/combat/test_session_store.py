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

    async def rpush(self, key, *values):
        self.lists.setdefault(key, []).extend(values)

    async def lrange(self, key, start, stop):
        values = self.lists.get(key, [])
        end = None if stop == -1 else stop + 1
        return values[start:end]


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
