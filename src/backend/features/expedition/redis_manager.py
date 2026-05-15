from __future__ import annotations

from typing import Any

from src.backend.infrastructure.redis.keys import ExpeditionActiveKey, ExpeditionRunKey


class ExpeditionRedisManager:
    DEFAULT_TTL_SECONDS = 7 * 24 * 60 * 60

    def __init__(self, redis, *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self.redis = redis
        self.ttl_seconds = ttl_seconds
        self.active_key = ExpeditionActiveKey()
        self.run_key = ExpeditionRunKey()

    def _client(self) -> Any:
        if hasattr(self.redis, "redis_client"):
            return self.redis.redis_client
        return self.redis.pipeline.client

    def build_active_key(self, char_id: int) -> str:
        return self.active_key.build(char_id=char_id)

    def build_run_key(self, run_id: str) -> str:
        return self.run_key.build(run_id=run_id)

    async def set_active_run(self, char_id: int, run_id: str) -> None:
        await self._client().set(self.build_active_key(char_id), run_id, ex=self.ttl_seconds)

    async def get_active_run(self, char_id: int) -> str | None:
        value = await self._client().get(self.build_active_key(char_id))
        if value is None:
            return None
        return value.decode() if isinstance(value, bytes) else str(value)

    async def clear_active_run(self, char_id: int) -> None:
        await self._client().delete(self.build_active_key(char_id))

    async def save_runtime(self, run_id: str, payload: dict[str, Any]) -> None:
        await self.redis.json_module.set(self.build_run_key(run_id), "$", payload)
        await self._client().expire(self.build_run_key(run_id), self.ttl_seconds)

    async def delete_runtime(self, run_id: str) -> None:
        await self._client().delete(self.build_run_key(run_id))
