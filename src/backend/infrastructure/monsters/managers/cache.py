from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService


ANCHOR_PROJECTION_REDIS_PREFIX = "game:monster:anchor_projection"


class MonsterGroupCacheManager:
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


class AnchorProjectionSnapshotCacheManager:
    def __init__(self, redis: Any) -> None:
        self.redis = redis

    async def save_snapshots(self, snapshots: dict[str, dict[str, Any]]) -> None:
        await self.redis.json_module.set(self.build_index_key(), "$", {"variants": sorted(snapshots)})
        for variant_id, snapshot in snapshots.items():
            await self.redis.json_module.set(self.build_snapshot_key(variant_id), "$", snapshot)

    @staticmethod
    def build_index_key() -> str:
        return f"{ANCHOR_PROJECTION_REDIS_PREFIX}:index"

    @staticmethod
    def build_snapshot_key(variant_id: str) -> str:
        return f"{ANCHOR_PROJECTION_REDIS_PREFIX}:{variant_id}"


class AnchorProjectionSnapshotCache:
    """Reads system anchor combat snapshots prepared during game bootstrap."""

    def __init__(self, redis: Any) -> None:
        self.redis = redis

    async def get_snapshot(self, variant_id: str) -> dict[str, Any] | None:
        key = AnchorProjectionSnapshotCacheManager.build_snapshot_key(variant_id)
        result = await self.redis.json_module.get(key, "$")
        if isinstance(result, list):
            return result[0] if result and isinstance(result[0], dict) else None
        return result if isinstance(result, dict) else None
