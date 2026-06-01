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

    async def list_progress(self, *, scan_count: int = 200) -> list[dict[str, Any]]:
        client = self._redis_client()
        cursor = 0
        rows: list[dict[str, Any]] = []
        while True:
            cursor, keys = await client.scan(cursor=cursor, match=self.build_pattern(), count=scan_count)
            for key in keys:
                result = await self.redis.json_module.get(key, "$")
                doc = self._first(result)
                if isinstance(doc, dict):
                    rows.append(doc)
            if cursor == 0:
                return rows

    async def delete_progress(self, run_id: str) -> None:
        await self.redis.string.delete(self.build_key(run_id))

    async def clear_all_progress(self, *, scan_count: int = 200, preserve_family_pressure: bool = False) -> int:
        client = self._redis_client()
        cursor = 0
        deleted = 0
        while True:
            cursor, keys = await client.scan(cursor=cursor, match=self.build_pattern(), count=scan_count)
            delete_keys = []
            for key in keys:
                if preserve_family_pressure:
                    result = await self.redis.json_module.get(key, "$")
                    doc = self._first(result)
                    if self._is_family_pressure(doc):
                        continue
                delete_keys.append(key)
            if delete_keys:
                deleted += int(await client.delete(*delete_keys))
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

    @staticmethod
    def _is_family_pressure(doc: Any) -> bool:
        if not isinstance(doc, dict):
            return False
        raw_metadata = doc.get("metadata")
        metadata = raw_metadata if isinstance(raw_metadata, dict) else {}
        raw_telemetry = doc.get("telemetry")
        telemetry = raw_telemetry if isinstance(raw_telemetry, dict) else {}
        return bool(metadata.get("family_pressure")) or str(telemetry.get("run_kind") or "") == "family_pressure"
