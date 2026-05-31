from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.infrastructure.redis.keys import CombatAiSimulationProgressKey

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService


class CombatAiSimulationProgressManager:
    """RedisJSON store for volatile admin simulation progress."""

    DEFAULT_TTL_SECONDS = 6 * 60 * 60

    def __init__(self, redis: RedisService, *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self.redis = redis
        self.key = CombatAiSimulationProgressKey()
        self.ttl_seconds = int(ttl_seconds)

    def build_key(self, run_id: str) -> str:
        return self.key.build(run_id=str(run_id))

    def build_pattern(self) -> str:
        return self.key.build(run_id="*")

    async def set_progress(self, run_id: str, payload: dict[str, Any]) -> None:
        key = self.build_key(run_id)
        await self.redis.json_module.set(key, "$", dict(payload))
        await self.redis.string.expire(key, self.ttl_seconds)

    async def get_progress(self, run_id: str) -> dict[str, Any] | None:
        result = await self.redis.json_module.get(self.build_key(run_id), "$")
        doc = self._first(result)
        return doc if isinstance(doc, dict) else None

    async def delete_progress(self, run_id: str) -> None:
        await self.redis.string.delete(self.build_key(run_id))

    async def clear_all_progress(self, *, scan_count: int = 200) -> int:
        client = self._redis_client()
        cursor = 0
        deleted = 0
        while True:
            cursor, keys = await client.scan(cursor=cursor, match=self.build_pattern(), count=scan_count)
            if keys:
                deleted += int(await client.delete(*keys))
            if cursor == 0:
                return deleted

    def _redis_client(self) -> Any:
        if hasattr(self.redis, "redis_client"):
            return self.redis.redis_client
        return self.redis.pipeline.client

    @staticmethod
    def _first(result: Any) -> Any:
        if isinstance(result, list):
            return result[0] if result else None
        return result
