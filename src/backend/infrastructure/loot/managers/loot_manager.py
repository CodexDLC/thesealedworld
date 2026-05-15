from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger as log

from src.shared.schemas.loot import CorpseDTO, LootContainerDTO

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService

_CORPSE_KEY = "loot:corpse:{corpse_id}"
_LOC_KEY = "loot:loc:{location_id}"
_ORDERED_KEY = "loot:ordered:{session_id}"


def _corpse_key(corpse_id: str) -> str:
    return _CORPSE_KEY.format(corpse_id=corpse_id)


def _loc_key(location_id: str) -> str:
    return _LOC_KEY.format(location_id=location_id)


def _ordered_key(session_id: str) -> str:
    return _ORDERED_KEY.format(session_id=session_id)


class LootManager:
    """RedisJSON access layer for loot corpses and location indexes."""

    def __init__(self, redis: RedisService) -> None:
        self.redis = redis

    def _client(self) -> Any:
        if hasattr(self.redis, "redis_client"):
            return self.redis.redis_client
        return self.redis.pipeline.client

    # ------------------------------------------------------------------
    # Corpse persistence
    # ------------------------------------------------------------------

    async def save_corpse(self, corpse: CorpseDTO, location_id: str, ttl: int) -> None:
        key = _corpse_key(corpse.id)
        await self.redis.json_module.set(key, "$", corpse.model_dump(mode="json"))
        await self.redis.string.expire(key, ttl)
        await self._client().sadd(_loc_key(location_id), corpse.id)
        await self._client().expire(_loc_key(location_id), ttl)

    async def get_corpse(self, corpse_id: str) -> CorpseDTO | None:
        result = await self.redis.json_module.get(_corpse_key(corpse_id), "$")
        if not result:
            return None
        data = result[0] if isinstance(result, list) else result
        try:
            return CorpseDTO.model_validate(data)
        except Exception as exc:
            log.error("LootManager | failed to parse corpse {}: {}", corpse_id, exc)
            return None

    async def patch_corpse(self, corpse_id: str, fields: dict[str, Any]) -> None:
        """Patch individual JSON paths on a corpse. fields = {"$.is_visible": True, ...}"""
        key = _corpse_key(corpse_id)
        for path, value in fields.items():
            await self.redis.json_module.set(key, path, value)

    async def set_ttl(self, corpse_id: str, seconds: int) -> None:
        await self.redis.string.expire(_corpse_key(corpse_id), seconds)

    # ------------------------------------------------------------------
    # Item removal from corpse (for claim flow)
    # ------------------------------------------------------------------

    async def remove_items_from_corpse(
        self, corpse_id: str, instance_ids: set[str], resource_template_ids: set[str]
    ) -> CorpseDTO | None:
        """Remove claimed items from corpse JSON, return updated CorpseDTO."""
        corpse = await self.get_corpse(corpse_id)
        if corpse is None:
            return None

        remaining = [
            item
            for item in corpse.items
            if item.instance_id not in instance_ids and item.template_id not in resource_template_ids
        ]
        corpse = corpse.model_copy(update={"items": remaining})
        await self.redis.json_module.set(
            _corpse_key(corpse_id), "$.items", [i.model_dump(mode="json") for i in remaining]
        )
        return corpse

    # ------------------------------------------------------------------
    # Location index
    # ------------------------------------------------------------------

    async def get_location_corpse_ids(self, location_id: str) -> set[str]:
        raw = await self._client().smembers(_loc_key(location_id))
        return {v.decode() if isinstance(v, bytes) else str(v) for v in raw}

    async def remove_from_location(self, location_id: str, corpse_id: str) -> None:
        await self._client().srem(_loc_key(location_id), corpse_id)

    # ------------------------------------------------------------------
    # Location loot fetch (returns all visible corpses)
    # ------------------------------------------------------------------

    async def get_location_loot(self, location_id: str) -> LootContainerDTO:
        ids = await self.get_location_corpse_ids(location_id)
        if not ids:
            return LootContainerDTO(location_id=location_id)

        corpses: list[CorpseDTO] = []
        stale_ids: list[str] = []

        for cid in ids:
            corpse = await self.get_corpse(cid)
            if corpse is None:
                stale_ids.append(cid)
                continue
            if corpse.is_visible:
                corpses.append(corpse)

        if stale_ids:
            client = self._client()
            for sid in stale_ids:
                await client.srem(_loc_key(location_id), sid)

        return LootContainerDTO(corpses=corpses, location_id=location_id)

    # ------------------------------------------------------------------
    # Combat loot-ordered marker (idempotency guard)
    # ------------------------------------------------------------------

    async def mark_loot_ordered(self, session_id: str) -> bool:
        """Set if not exists. Returns True if we are the first to set it."""
        key = _ordered_key(session_id)
        result = await self._client().set(key, "1", ex=86400, nx=True)
        return bool(result)

    async def is_loot_ordered(self, session_id: str) -> bool:
        return bool(await self._client().exists(_ordered_key(session_id)))
