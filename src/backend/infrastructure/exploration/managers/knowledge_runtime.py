from __future__ import annotations

from typing import Any


class ExplorationKnowledgeRuntimeManager:
    DEFAULT_TTL_SECONDS = 6 * 60 * 60

    def __init__(self, redis: Any, *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self.redis = redis
        self.ttl_seconds = ttl_seconds

    def build_key(self, char_id: int, loc_id: str) -> str:
        return f"game:exploration:knowledge:{int(char_id)}:{loc_id}"

    def build_dirty_key(self, char_id: int) -> str:
        return f"game:exploration:knowledge:dirty:{int(char_id)}"

    async def get(self, char_id: int, loc_id: str) -> dict[str, Any] | None:
        result = await self.redis.json_module.get(self.build_key(char_id, loc_id), "$")
        doc = self._first(result)
        return dict(doc) if isinstance(doc, dict) else None

    async def set(self, char_id: int, loc_id: str, payload: dict[str, Any], *, mark_dirty: bool = True) -> None:
        key = self.build_key(char_id, loc_id)
        document = {"character_id": int(char_id), "loc_id": str(loc_id), **dict(payload)}
        await self.redis.json_module.set(key, "$", document)
        await self.redis.string.expire(key, self.ttl_seconds)
        if mark_dirty:
            await self.mark_dirty(char_id, loc_id)

    async def mark_dirty(self, char_id: int, loc_id: str) -> None:
        dirty_key = self.build_dirty_key(char_id)
        result = await self.redis.json_module.get(dirty_key, "$")
        doc = self._first(result)
        dirty = dict(doc) if isinstance(doc, dict) else {}
        loc_ids = [str(item) for item in dirty.get("loc_ids", []) if str(item)]
        if str(loc_id) not in loc_ids:
            loc_ids.append(str(loc_id))
        await self.redis.json_module.set(dirty_key, "$", {"char_id": int(char_id), "loc_ids": loc_ids})
        await self.redis.string.expire(dirty_key, self.ttl_seconds)

    async def dirty_loc_ids(self, char_id: int, *, limit: int = 100) -> list[str]:
        result = await self.redis.json_module.get(self.build_dirty_key(char_id), "$")
        doc = self._first(result)
        if not isinstance(doc, dict):
            return []
        loc_ids = [str(item) for item in doc.get("loc_ids", []) if str(item)]
        return loc_ids[:limit]

    async def clear_dirty(self, char_id: int, loc_ids: list[str]) -> None:
        if not loc_ids:
            return
        dirty_key = self.build_dirty_key(char_id)
        result = await self.redis.json_module.get(dirty_key, "$")
        doc = self._first(result)
        if not isinstance(doc, dict):
            return
        clear_set = {str(loc_id) for loc_id in loc_ids}
        remaining = [str(item) for item in doc.get("loc_ids", []) if str(item) not in clear_set]
        if remaining:
            await self.redis.json_module.set(dirty_key, "$", {"char_id": int(char_id), "loc_ids": remaining})
            await self.redis.string.expire(dirty_key, self.ttl_seconds)
            return
        await self.redis.string.delete(dirty_key)

    async def scan_dirty_char_ids(self, *, limit: int = 100) -> list[int]:
        client = self._redis_client()
        cursor = 0
        result: list[int] = []
        while True:
            cursor, keys = await client.scan(
                cursor=cursor,
                match="game:exploration:knowledge:dirty:*",
                count=limit,
            )
            for key in keys:
                char_id = self._char_id_from_dirty_key(str(key))
                if char_id is None:
                    continue
                if await self.dirty_loc_ids(char_id, limit=1):
                    result.append(char_id)
            if cursor == 0 or len(result) >= limit:
                return result[:limit]

    def _redis_client(self) -> Any:
        if hasattr(self.redis, "redis_client"):
            return self.redis.redis_client
        return self.redis.pipeline.client

    @staticmethod
    def _first(result: Any) -> Any:
        if isinstance(result, list):
            return result[0] if result else None
        return result

    @staticmethod
    def _char_id_from_dirty_key(key: str) -> int | None:
        prefix = "game:exploration:knowledge:dirty:"
        if not key.startswith(prefix):
            return None
        raw = key.removeprefix(prefix)
        if not raw.isdigit():
            return None
        return int(raw)
