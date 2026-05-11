from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService


class MonsterGroupCacheIntegration:
    """Stores encounter-facing monster group presentation data."""

    def __init__(self, redis: RedisService) -> None:
        self.redis = redis

    def build_group_key(self, group_id: str) -> str:
        return f"game:monster:group:{group_id}"

    async def save_group(self, group_id: str, payload: dict[str, Any], *, ttl: int) -> str:
        key = self.build_group_key(group_id)
        await self.redis.json_module.set(key, "$", dict(payload))
        await self.redis.string.expire(key, int(ttl))
        return key
