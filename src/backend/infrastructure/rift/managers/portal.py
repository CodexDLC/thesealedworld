from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService


class RiftPortalStore:
    DEFAULT_TTL_SECONDS = 60 * 60
    ACTIVE_STATUSES = {"active"}
    CLOSED_STATUSES = {"completed", "failed_sealed", "abandoned", "expired"}
    KEY_PREFIX = "game:rift:portal:"

    def __init__(self, redis: RedisService, *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self.redis = redis
        self.ttl_seconds = ttl_seconds

    def build_portal_key(self, portal_id: str) -> str:
        return f"{self.KEY_PREFIX}{portal_id}"

    async def save_portal(self, payload: dict[str, Any]) -> dict[str, Any]:
        portal_id = str(payload.get("portal_id") or "")
        if not portal_id:
            raise ValueError("Rift portal payload must contain portal_id")
        document = dict(payload)
        now = time.time()
        document.setdefault("status", "active")
        document.setdefault("created_at", now)
        document["updated_at"] = now
        key = self.build_portal_key(portal_id)
        await self.redis.json_module.set(key, "$", document)
        await self.redis.string.expire(key, self.ttl_seconds)
        return document

    async def get_portal(self, portal_id: str) -> dict[str, Any] | None:
        result = await self.redis.json_module.get(self.build_portal_key(portal_id), "$")
        doc = self._first(result)
        return dict(doc) if isinstance(doc, dict) else None

    async def find_by_rift_session(self, rift_session_id: str, *, limit: int = 100) -> dict[str, Any] | None:
        for portal in await self.scan(limit=limit):
            if str(portal.get("rift_session_id") or "") == str(rift_session_id):
                return portal
        return None

    async def mark_status(
        self,
        portal_id: str,
        *,
        status: str,
        reason: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        portal = await self.get_portal(portal_id)
        if portal is None:
            return None
        now = time.time()
        portal["status"] = status
        portal["updated_at"] = now
        if reason:
            portal["status_reason"] = reason
        if details:
            portal["details"] = {**dict(portal.get("details") or {}), **details}
        if status in self.CLOSED_STATUSES and not portal.get("closed_at"):
            portal["closed_at"] = now
        if status == "archived" and not portal.get("archived_at"):
            portal["archived_at"] = now
        return await self.save_portal(portal)

    async def scan(self, *, limit: int = 100) -> list[dict[str, Any]]:
        client = self._redis_client()
        cursor = 0
        result: list[dict[str, Any]] = []
        while True:
            cursor, keys = await client.scan(cursor=cursor, match=f"{self.KEY_PREFIX}*", count=limit)
            for key in keys:
                portal_id = str(key).removeprefix(self.KEY_PREFIX)
                portal = await self.get_portal(portal_id)
                if portal is not None:
                    result.append(portal)
                if len(result) >= limit:
                    return result[:limit]
            if cursor == 0:
                return result[:limit]

    async def archive_due(self, *, now: float | None = None, limit: int = 100) -> list[dict[str, Any]]:
        timestamp = time.time() if now is None else float(now)
        archived: list[dict[str, Any]] = []
        for portal in await self.scan(limit=limit):
            portal_id = str(portal.get("portal_id") or "")
            if not portal_id or portal.get("status") == "archived":
                continue
            expires_at = _optional_float(portal.get("expires_at"))
            if portal.get("status") in self.ACTIVE_STATUSES and expires_at is not None and expires_at <= timestamp:
                updated = await self.mark_status(portal_id, status="archived", reason="expired")
            elif portal.get("status") in self.CLOSED_STATUSES:
                updated = await self.mark_status(portal_id, status="archived", reason=str(portal.get("status")))
            else:
                updated = None
            if updated is not None:
                archived.append(updated)
        return archived

    def _redis_client(self) -> Any:
        if hasattr(self.redis, "redis_client"):
            return self.redis.redis_client
        return self.redis.pipeline.client

    @staticmethod
    def _first(result: Any) -> Any:
        if isinstance(result, list):
            return result[0] if result else None
        return result


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
