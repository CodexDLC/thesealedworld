from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService


T = TypeVar("T")


class RiftRestoreLock:
    DEFAULT_TTL_SECONDS = 30
    KEY_PREFIX = "game:rift:restore-lock:"

    def __init__(self, redis: RedisService, *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self.redis = redis
        self.ttl_seconds = ttl_seconds

    def build_lock_key(self, rift_instance_id: str) -> str:
        return f"{self.KEY_PREFIX}{rift_instance_id}"

    async def run_once(self, rift_instance_id: str, callback: Callable[[], Awaitable[T]]) -> T:
        key = self.build_lock_key(rift_instance_id)
        client = self._redis_client()
        acquired = await client.set(key, "1", ex=self.ttl_seconds, nx=True)
        if not acquired:
            exists = getattr(client, "exists", None)
            if exists is not None:
                for _ in range(20):
                    if not await exists(key):
                        break
                    await asyncio.sleep(0.05)
            return await callback()
        try:
            return await callback()
        finally:
            if hasattr(client, "delete"):
                await client.delete(key)

    def _redis_client(self):
        if hasattr(self.redis, "redis_client"):
            return self.redis.redis_client
        return self.redis.pipeline.client
