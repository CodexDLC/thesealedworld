from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService


class RiftRunSessionNotFoundError(RuntimeError):
    pass


class RiftRunSessionStore:
    DEFAULT_TTL_SECONDS = 60 * 60
    KEY_PREFIX = "game:rift:session:"

    def __init__(self, redis: RedisService, *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self.redis = redis
        self.ttl_seconds = ttl_seconds

    def build_session_key(self, rift_session_id: str) -> str:
        return f"{self.KEY_PREFIX}{rift_session_id}"

    async def create_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("rift_session_id") or "")
        if not session_id:
            raise ValueError("Rift session payload must contain rift_session_id")
        key = self.build_session_key(session_id)
        await self.redis.json_module.set(key, "$", dict(payload))
        await self.redis.string.expire(key, self.ttl_seconds)
        return dict(payload)

    async def save_session(
        self,
        payload: dict[str, Any],
        *,
        dirty_reason: str | None = None,
        dirty_paths: list[str] | None = None,
    ) -> None:
        document = dict(payload)
        if dirty_reason:
            document["is_dirty"] = True
            document["dirty"] = _dirty_marker(dirty_reason, dirty_paths or ["$"])
        await self.create_session(document)

    async def get_session(self, rift_session_id: str) -> dict[str, Any] | None:
        result = await self.redis.json_module.get(self.build_session_key(rift_session_id), "$")
        doc = self._first(result)
        return dict(doc) if isinstance(doc, dict) else None

    async def require_session(self, rift_session_id: str) -> dict[str, Any]:
        session = await self.get_session(rift_session_id)
        if session is None:
            raise RiftRunSessionNotFoundError(f"Rift run session not found: {rift_session_id}")
        return session

    async def set_position(
        self,
        rift_session_id: str,
        *,
        current_node_id: str,
        previous_node_id: str | None = None,
        heading: str | None = None,
    ) -> None:
        key = self.build_session_key(rift_session_id)
        await self.redis.json_module.set(key, "$.current_node_id", current_node_id)
        await self.redis.json_module.set(key, "$.previous_node_id", previous_node_id)
        await self.redis.json_module.set(key, "$.heading", heading)
        await self.mark_dirty(
            rift_session_id,
            reason="position_updated",
            paths=["$.current_node_id", "$.previous_node_id", "$.heading"],
        )

    async def set_visited(self, rift_session_id: str, node_ids: set[str]) -> None:
        await self.redis.json_module.set(
            self.build_session_key(rift_session_id),
            "$.visited_node_ids",
            sorted(node_ids),
        )
        await self.mark_dirty(rift_session_id, reason="visited_updated", paths=["$.visited_node_ids"])

    async def set_discovered(self, rift_session_id: str, node_ids: set[str]) -> None:
        await self.redis.json_module.set(
            self.build_session_key(rift_session_id),
            "$.discovered_node_ids",
            sorted(node_ids),
        )
        await self.mark_dirty(rift_session_id, reason="discovered_updated", paths=["$.discovered_node_ids"])

    async def start_travel(self, rift_session_id: str, travel: dict[str, Any]) -> None:
        await self.redis.json_module.set(self.build_session_key(rift_session_id), "$.active_travel", dict(travel))
        await self.mark_dirty(rift_session_id, reason="travel_started", paths=["$.active_travel"])

    async def interrupt_travel(self, rift_session_id: str, travel: dict[str, Any]) -> None:
        payload = {**travel, "status": "interrupted"}
        await self.redis.json_module.set(self.build_session_key(rift_session_id), "$.active_travel", payload)
        await self.mark_dirty(rift_session_id, reason="travel_interrupted", paths=["$.active_travel"])

    async def complete_travel(self, rift_session_id: str, *, last_travel: dict[str, Any]) -> None:
        key = self.build_session_key(rift_session_id)
        await self.redis.json_module.set(key, "$.active_travel", None)
        await self.redis.json_module.set(key, "$.last_travel", dict(last_travel))
        await self.mark_dirty(rift_session_id, reason="travel_completed", paths=["$.active_travel", "$.last_travel"])

    async def set_active_encounter(self, rift_session_id: str, encounter_id: str) -> None:
        await self.redis.json_module.set(self.build_session_key(rift_session_id), "$.active_encounter_id", encounter_id)
        await self.mark_dirty(rift_session_id, reason="active_encounter_started", paths=["$.active_encounter_id"])

    async def clear_active_encounter(self, rift_session_id: str) -> None:
        await self.redis.json_module.set(self.build_session_key(rift_session_id), "$.active_encounter_id", None)
        await self.mark_dirty(rift_session_id, reason="active_encounter_cleared", paths=["$.active_encounter_id"])

    async def mark_dirty(self, rift_session_id: str, *, reason: str, paths: list[str]) -> None:
        key = self.build_session_key(rift_session_id)
        await self.redis.json_module.set(key, "$.is_dirty", True)
        await self.redis.json_module.set(key, "$.dirty", _dirty_marker(reason, paths))
        await self.redis.string.expire(key, self.ttl_seconds)

    async def clear_dirty(self, rift_session_id: str) -> None:
        key = self.build_session_key(rift_session_id)
        await self.redis.json_module.set(key, "$.is_dirty", False)
        await self.redis.json_module.set(key, "$.dirty", {"dirty": False, "last_flushed_at": time.time()})
        await self.redis.string.expire(key, self.ttl_seconds)

    async def scan_dirty(self, *, limit: int = 100) -> list[str]:
        client = self._redis_client()
        cursor = 0
        result: list[str] = []
        while True:
            cursor, keys = await client.scan(cursor=cursor, match=f"{self.KEY_PREFIX}*", count=limit)
            for key in keys:
                session_id = self._session_id_from_key(str(key))
                if session_id is None:
                    continue
                session = await self.get_session(session_id)
                dirty = dict(session.get("dirty") or {}) if isinstance(session, dict) else {}
                if session and (session.get("is_dirty") is True or dirty.get("dirty") is True):
                    result.append(session_id)
                if len(result) >= limit:
                    return result[:limit]
            if cursor == 0:
                return result[:limit]

    async def delete_session(self, rift_session_id: str) -> None:
        await self.redis.string.delete(self.build_session_key(rift_session_id))

    def _redis_client(self) -> Any:
        if hasattr(self.redis, "redis_client"):
            return self.redis.redis_client
        return self.redis.pipeline.client

    @staticmethod
    def _first(result: Any) -> Any:
        if isinstance(result, list):
            return result[0] if result else None
        return result

    @classmethod
    def _session_id_from_key(cls, key: str) -> str | None:
        return key.removeprefix(cls.KEY_PREFIX) if key.startswith(cls.KEY_PREFIX) else None


def _dirty_marker(reason: str, paths: list[str]) -> dict[str, Any]:
    return {
        "dirty": True,
        "reason": reason,
        "paths": sorted(dict.fromkeys(paths)),
        "updated_at": time.time(),
    }
