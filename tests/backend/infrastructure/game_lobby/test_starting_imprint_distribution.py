from __future__ import annotations

from collections import defaultdict

import pytest

from src.backend.infrastructure.game_lobby.managers import StartingImprintDistributionManager


class FakeRedisService:
    def __init__(self) -> None:
        self.redis_client = FakeRedisClient()


class FakeRedisClient:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, int]] = defaultdict(dict)
        self.lists: dict[str, list[str]] = defaultdict(list)

    async def hgetall(self, key: str) -> dict[str, int]:
        return dict(self.hashes[key])

    async def lrange(self, key: str, start: int, stop: int) -> list[str]:
        values = self.lists[key]
        if stop < 0:
            stop = len(values) + stop
        return list(values[start : stop + 1])

    def pipeline(self, *, transaction: bool = True) -> FakePipeline:
        return FakePipeline(self, transaction=transaction)

    def hincrby(self, key: str, field: str, amount: int) -> None:
        self.hashes[key][field] = int(self.hashes[key].get(field, 0)) + int(amount)

    def lrem(self, key: str, count: int, value: str) -> None:
        self.lists[key] = [item for item in self.lists[key] if item != value]

    def lpush(self, key: str, value: str) -> None:
        self.lists[key].insert(0, value)

    def ltrim(self, key: str, start: int, stop: int) -> None:
        self.lists[key] = self.lists[key][start : stop + 1]


class FakePipeline:
    def __init__(self, client: FakeRedisClient, *, transaction: bool) -> None:
        self.client = client
        self.transaction = transaction

    async def __aenter__(self) -> FakePipeline:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def hincrby(self, key: str, field: str, amount: int) -> None:
        self.client.hincrby(key, field, amount)

    def lrem(self, key: str, count: int, value: str) -> None:
        self.client.lrem(key, count, value)

    def lpush(self, key: str, value: str) -> None:
        self.client.lpush(key, value)

    def ltrim(self, key: str, start: int, stop: int) -> None:
        self.client.ltrim(key, start, stop)

    async def execute(self) -> list[object]:
        return []


@pytest.mark.asyncio
async def test_select_and_record_uses_all_imprints_before_repeating() -> None:
    redis = FakeRedisService()
    manager = StartingImprintDistributionManager(redis)
    pool = tuple(f"starter_{index}" for index in range(11))

    selected = [
        await manager.select_and_record(user_id="user-1", seed=f"seed-{index}", imprint_keys=pool)
        for index in range(len(pool))
    ]

    assert set(selected) == set(pool)
    assert redis.redis_client.hashes[manager.build_usage_key()] == {key: 1 for key in pool}


@pytest.mark.asyncio
async def test_select_for_user_uses_seeded_tie_break() -> None:
    manager = StartingImprintDistributionManager(FakeRedisService())
    pool = ("starter_guard_01", "starter_archer_01", "starter_staff_01")

    first = await manager.select_for_user(user_id="user-1", seed="fixed-seed", imprint_keys=pool)
    second = await manager.select_for_user(user_id="user-1", seed="fixed-seed", imprint_keys=pool)

    assert first == second
    assert first in pool


@pytest.mark.asyncio
async def test_select_for_user_excludes_recent_imprints_when_possible() -> None:
    redis = FakeRedisService()
    manager = StartingImprintDistributionManager(redis)
    redis.redis_client.lists[manager.build_user_recent_key("user-1")] = ["starter_a", "starter_b"]

    selected = await manager.select_for_user(
        user_id="user-1",
        seed="fixed-seed",
        imprint_keys=("starter_a", "starter_b", "starter_c"),
    )

    assert selected == "starter_c"


@pytest.mark.asyncio
async def test_select_for_user_allows_full_pool_when_every_candidate_is_recent() -> None:
    redis = FakeRedisService()
    manager = StartingImprintDistributionManager(redis)
    pool = ("starter_a", "starter_b", "starter_c")
    redis.redis_client.lists[manager.build_user_recent_key("user-1")] = list(pool)
    redis.redis_client.hashes[manager.build_usage_key()] = {"starter_a": 0, "starter_b": 1, "starter_c": 2}

    selected = await manager.select_for_user(user_id="user-1", seed="fixed-seed", imprint_keys=pool)

    assert selected == "starter_a"


@pytest.mark.asyncio
async def test_record_selection_tracks_usage_and_deduped_recent_list() -> None:
    redis = FakeRedisService()
    manager = StartingImprintDistributionManager(redis)

    await manager.record_selection(user_id="user-1", imprint_key="starter_guard_01")
    await manager.record_selection(user_id="user-1", imprint_key="starter_archer_01")
    await manager.record_selection(user_id="user-1", imprint_key="starter_guard_01")

    assert redis.redis_client.hashes[manager.build_usage_key()] == {
        "starter_guard_01": 2,
        "starter_archer_01": 1,
    }
    assert redis.redis_client.lists[manager.build_user_recent_key("user-1")] == [
        "starter_guard_01",
        "starter_archer_01",
    ]
