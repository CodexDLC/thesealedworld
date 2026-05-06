from __future__ import annotations

from typing import Any

from src.shared.schemas.inventory import InventoryRuntimeSessionDTO


class InventorySessionManager:
    DEFAULT_TTL_SECONDS = 3600

    def __init__(self, redis: Any, *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self.redis = redis
        self.ttl_seconds = ttl_seconds

    def build_key(self, char_id: int) -> str:
        return f"game:inventory:{char_id}"

    async def get(self, char_id: int) -> InventoryRuntimeSessionDTO | None:
        result = await self.redis.json_module.get(self.build_key(char_id), "$")
        doc = self._first(result)
        return InventoryRuntimeSessionDTO.model_validate(doc) if isinstance(doc, dict) else None

    async def set(self, session: InventoryRuntimeSessionDTO) -> None:
        key = self.build_key(session.char_id)
        await self.redis.json_module.set(key, "$", session.model_dump(mode="json"))
        await self.touch(session.char_id)

    async def touch(self, char_id: int) -> None:
        await self.redis.string.expire(self.build_key(char_id), self.ttl_seconds)

    async def delete(self, char_id: int) -> None:
        await self.redis.string.delete(self.build_key(char_id))

    @staticmethod
    def _first(result: Any) -> Any:
        if isinstance(result, list):
            return result[0] if result else None
        return result
