from __future__ import annotations

import time
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

    async def patch_fields(self, char_id: int, updates: dict[str, Any]) -> None:
        if not updates:
            return
        key = self.build_key(char_id)
        async with self._redis_client().pipeline(transaction=False) as pipe:
            for path, value in updates.items():
                pipe.json().set(key, path, value)
            pipe.expire(key, self.ttl_seconds)
            await pipe.execute()

    async def mark_dirty(self, char_id: int, *, reason: str, paths: list[str]) -> None:
        dirty = {
            "dirty": True,
            "reason": reason,
            "paths": paths,
            "updated_at": time.time(),
        }
        await self.patch_fields(
            char_id,
            {
                "$.is_dirty": True,
                "$.dirty": dirty,
            },
        )

    async def clear_dirty(self, char_id: int) -> None:
        await self.patch_fields(
            char_id,
            {
                "$.is_dirty": False,
                "$.dirty": {"dirty": False, "last_flushed_at": time.time()},
            },
        )

    async def scan_dirty(self, *, limit: int = 100) -> list[int]:
        client = self._redis_client()
        cursor = 0
        result: list[int] = []
        while True:
            cursor, keys = await client.scan(cursor=cursor, match="game:inventory:*", count=limit)
            for key in keys:
                char_id = self._char_id_from_key(str(key))
                if char_id is None:
                    continue
                session = await self.get(char_id)
                if session and (session.is_dirty or session.dirty.get("dirty") is True):
                    result.append(char_id)
            if cursor == 0 or len(result) >= limit:
                return result[:limit]

    async def touch(self, char_id: int) -> None:
        await self.redis.string.expire(self.build_key(char_id), self.ttl_seconds)

    async def delete(self, char_id: int) -> None:
        await self.redis.string.delete(self.build_key(char_id))

    @staticmethod
    def _first(result: Any) -> Any:
        if isinstance(result, list):
            return result[0] if result else None
        return result

    def _redis_client(self) -> Any:
        if hasattr(self.redis, "redis_client"):
            return self.redis.redis_client
        return self.redis.pipeline.client

    @staticmethod
    def _char_id_from_key(key: str) -> int | None:
        prefix = "game:inventory:"
        if not key.startswith(prefix):
            return None
        raw = key.removeprefix(prefix)
        if not raw.isdigit():
            return None
        return int(raw)
