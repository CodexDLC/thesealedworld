from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService


class ExplorationEncounterRuntimeManager:
    DEFAULT_TTL_SECONDS = 30 * 60

    def __init__(self, redis: RedisService) -> None:
        self.redis = redis

    def build_encounter_key(self, encounter_id: str) -> str:
        return f"game:encounter:{encounter_id}"

    async def create_session(
        self,
        encounter_id: str,
        payload: dict[str, Any],
        *,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> dict[str, Any]:
        session = dict(payload)
        session.setdefault("encounter_id", encounter_id)
        key = self.build_encounter_key(encounter_id)
        await self.redis.json_module.set(key, "$", copy.deepcopy(session))
        await self.redis.string.expire(key, int(ttl_seconds))
        return copy.deepcopy(session)

    async def get_session(self, encounter_id: str) -> dict[str, Any] | None:
        result = await self.redis.json_module.get(self.build_encounter_key(encounter_id), "$")
        payload = self._first(result)
        return copy.deepcopy(payload) if isinstance(payload, dict) else None

    async def patch_session(self, encounter_id: str, updates: dict[str, Any]) -> None:
        if not updates:
            return
        key = self.build_encounter_key(encounter_id)
        async with self._redis_client().pipeline(transaction=False) as pipe:
            for path, value in updates.items():
                json_path = path if path.startswith("$.") else f"$.{path}"
                pipe.json().set(key, json_path, value)
            await pipe.execute()

    async def clear_session(self, encounter_id: str) -> None:
        await self.redis.string.delete(self.build_encounter_key(encounter_id))

    async def list_session_summaries(self, *, limit: int = 100) -> list[dict[str, Any]]:
        client = self._redis_client()
        keys: list[Any] = []
        cursor = 0
        while True:
            cursor, batch = await client.scan(cursor, match="game:encounter:*", count=limit)
            keys.extend(batch)
            if cursor == 0:
                break

        results: list[dict[str, Any]] = []
        for key in keys:
            try:
                raw = await self.redis.json_module.get(key, "$")
                doc = self._first(raw)
                if not isinstance(doc, dict):
                    continue
                payload = doc.get("payload") or {}
                payload = payload if isinstance(payload, dict) else {}
                results.append(
                    {
                        "encounter_id": doc.get("encounter_id", "-"),
                        "char_id": str(doc.get("char_id", "-")),
                        "status": doc.get("status", "-"),
                        "type": payload.get("type", "-"),
                        "title": payload.get("title", "-"),
                    }
                )
            except Exception:  # nosec B112
                continue
        return results

    async def get_monster_cache(self, cache_key: str) -> dict[str, Any] | None:
        result = await self.redis.json_module.get(cache_key, "$")
        payload = self._first(result)
        return copy.deepcopy(payload) if isinstance(payload, dict) else None

    async def set_monster_cache(
        self,
        cache_key: str,
        payload: dict[str, Any],
        *,
        ttl_seconds: int | None = None,
    ) -> None:
        await self.redis.json_module.set(cache_key, "$", dict(payload))
        if ttl_seconds is not None:
            await self.redis.string.expire(cache_key, int(ttl_seconds))

    def _redis_client(self) -> Any:
        if hasattr(self.redis, "redis_client"):
            return self.redis.redis_client
        return self.redis.pipeline.client

    @staticmethod
    def _first(result: Any) -> Any:
        if isinstance(result, list):
            return result[0] if result else None
        return result
