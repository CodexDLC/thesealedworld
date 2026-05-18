from types import SimpleNamespace

import pytest

from src.backend.features.loot.workers.tasks.loot_claim_task import _clear_inventory_runtime_cache


class FakeStringRedis:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    async def delete(self, key: str) -> bool:
        self.deleted.append(key)
        return True


@pytest.mark.asyncio
async def test_clear_inventory_runtime_cache_removes_open_inventory_session() -> None:
    redis = SimpleNamespace(string=FakeStringRedis())

    await _clear_inventory_runtime_cache({"redis_service": redis}, 7)

    assert redis.string.deleted == ["game:inventory:7"]


@pytest.mark.asyncio
async def test_clear_inventory_runtime_cache_is_noop_without_redis_service() -> None:
    await _clear_inventory_runtime_cache({}, 7)
