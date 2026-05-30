from __future__ import annotations

import random
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from src.backend.infrastructure.redis.keys import StartingImprintUsageKey, StartingImprintUserRecentKey

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService


class StartingImprintDistributionManager:
    """Balances automatic starting imprint assignment through Redis counters."""

    DEFAULT_RECENT_LIMIT = 3

    def __init__(self, redis: RedisService, *, recent_limit: int = DEFAULT_RECENT_LIMIT) -> None:
        self.redis = redis
        self.usage_key = StartingImprintUsageKey()
        self.user_recent_key = StartingImprintUserRecentKey()
        self.recent_limit = max(0, int(recent_limit))

    def build_usage_key(self) -> str:
        return self.usage_key.build()

    def build_user_recent_key(self, user_id: object) -> str:
        return self.user_recent_key.build(user_id=str(user_id))

    async def select_and_record(
        self,
        *,
        user_id: object,
        seed: str | None,
        imprint_keys: Sequence[str],
    ) -> str:
        selected = await self.select_for_user(user_id=user_id, seed=seed, imprint_keys=imprint_keys)
        await self.record_selection(user_id=user_id, imprint_key=selected)
        return selected

    async def select_for_user(
        self,
        *,
        user_id: object,
        seed: str | None,
        imprint_keys: Sequence[str],
    ) -> str:
        pool = tuple(dict.fromkeys(str(key) for key in imprint_keys if key))
        if not pool:
            raise ValueError("No starting imprints are available for distribution")

        client = self._redis_client()
        usage = self._usage_counts(await client.hgetall(self.build_usage_key()))
        recent = set(await client.lrange(self.build_user_recent_key(user_id), 0, max(0, self.recent_limit - 1)))
        candidates = tuple(key for key in pool if key not in recent)
        if not candidates:
            candidates = pool

        min_count = min(usage.get(key, 0) for key in candidates)
        tied = tuple(key for key in candidates if usage.get(key, 0) == min_count)
        rng = random.Random(seed) if seed is not None else random.SystemRandom()
        return rng.choice(tied)

    async def record_selection(self, *, user_id: object, imprint_key: str) -> None:
        key = str(imprint_key)
        if not key:
            raise ValueError("Starting imprint key must be non-empty")

        client = self._redis_client()
        recent_key = self.build_user_recent_key(user_id)
        async with client.pipeline(transaction=True) as pipe:
            pipe.hincrby(self.build_usage_key(), key, 1)
            if self.recent_limit > 0:
                pipe.lrem(recent_key, 0, key)
                pipe.lpush(recent_key, key)
                pipe.ltrim(recent_key, 0, self.recent_limit - 1)
            await pipe.execute()

    def _redis_client(self) -> Any:
        if hasattr(self.redis, "redis_client"):
            return self.redis.redis_client
        return self.redis.pipeline.client

    @staticmethod
    def _usage_counts(raw: dict[Any, Any]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for key, value in dict(raw or {}).items():
            try:
                counts[str(key)] = max(0, int(value))
            except (TypeError, ValueError):
                counts[str(key)] = 0
        return counts
