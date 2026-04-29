from typing import Any, Literal

from codex_platform.redis_service import RedisService

from src.backend.core.redis.keys import ActorSnapshotKey

ActorSnapshotSection = Literal["meta", "runtime", "combat", "inventory", "status", "source"]


class ActorSnapshotManager:
    """RedisJSON access layer for temporary actor snapshots.

    Snapshots are transport/cache objects used by features to bootstrap their
    own sessions. They are not the source of truth for long-term persistence.
    """

    DEFAULT_TTL_SECONDS = 300

    def __init__(self, redis: RedisService) -> None:
        self.redis = redis
        self.key = ActorSnapshotKey()

    def build_key(self, snapshot_id: str) -> str:
        return self.key.build(snapshot_id=snapshot_id)

    def _redis_client(self) -> Any:
        if hasattr(self.redis, "redis_client"):
            return self.redis.redis_client
        return self.redis.pipeline.client

    async def save_snapshot(self, snapshot_id: str, data: dict[str, Any], ttl: int = DEFAULT_TTL_SECONDS) -> str:
        snapshot_key = self.build_key(snapshot_id)
        await self.redis.json_module.set(snapshot_key, "$", self._normalize_snapshot(data))
        await self.redis.string.expire(snapshot_key, ttl)
        return snapshot_key

    async def save_snapshots(
        self,
        snapshots: dict[str, dict[str, Any]],
        ttl: int = DEFAULT_TTL_SECONDS,
    ) -> dict[str, str]:
        """Batch-save multiple snapshots in one Redis pipeline.

        Returns ``{snapshot_id: snapshot_key}`` for entries that were written.
        On full pipeline failure returns an empty mapping.
        """
        if not snapshots:
            return {}

        ordered_ids = list(snapshots.keys())
        keys_by_id = {sid: self.build_key(sid) for sid in ordered_ids}

        try:
            async with self._redis_client().pipeline(transaction=False) as pipe:
                for sid in ordered_ids:
                    key = keys_by_id[sid]
                    normalized = self._normalize_snapshot(snapshots[sid])
                    pipe.json().set(key, "$", normalized)
                    pipe.expire(key, ttl)
                results = await pipe.execute(raise_on_error=False)
        except Exception:
            return {}

        saved: dict[str, str] = {}
        for index, sid in enumerate(ordered_ids):
            set_result = results[index * 2] if index * 2 < len(results) else None
            expire_result = results[index * 2 + 1] if index * 2 + 1 < len(results) else None
            if isinstance(set_result, Exception) or isinstance(expire_result, Exception):
                continue
            if not set_result:
                continue
            saved[sid] = keys_by_id[sid]
        return saved

    async def get_snapshot(self, snapshot_key: str) -> dict[str, Any] | None:
        result = await self.redis.json_module.get(snapshot_key, "$")
        return self._first(result)

    async def get_snapshots_batch(self, snapshot_keys: list[str]) -> dict[str, dict[str, Any] | None]:
        if not snapshot_keys:
            return {}

        try:
            async with self._redis_client().pipeline(transaction=False) as pipe:
                for key in snapshot_keys:
                    pipe.json().get(key, "$")
                results = await pipe.execute(raise_on_error=False)
        except Exception:
            return {key: None for key in snapshot_keys}

        return {
            key: None if i >= len(results) or isinstance(results[i], Exception) else self._first(results[i])
            for i, key in enumerate(snapshot_keys)
        }

    async def get_section(self, snapshot_key: str, section: ActorSnapshotSection) -> dict[str, Any] | None:
        result = await self.redis.json_module.get(snapshot_key, f"$.{section}")
        return self._first(result)

    async def get_sections_batch(
        self,
        snapshot_keys: list[str],
        section: ActorSnapshotSection,
    ) -> dict[str, dict[str, Any] | None]:
        if not snapshot_keys:
            return {}

        path = f"$.{section}"

        try:
            async with self._redis_client().pipeline(transaction=False) as pipe:
                for key in snapshot_keys:
                    pipe.json().get(key, path)
                results = await pipe.execute(raise_on_error=False)
        except Exception:
            return {key: None for key in snapshot_keys}

        return {
            key: None if i >= len(results) or isinstance(results[i], Exception) else self._first(results[i])
            for i, key in enumerate(snapshot_keys)
        }

    async def get_meta(self, snapshot_key: str) -> dict[str, Any] | None:
        return await self.get_section(snapshot_key, "meta")

    async def get_runtime(self, snapshot_key: str) -> dict[str, Any] | None:
        return await self.get_section(snapshot_key, "runtime")

    async def get_combat(self, snapshot_key: str) -> dict[str, Any] | None:
        return await self.get_section(snapshot_key, "combat")

    async def get_inventory(self, snapshot_key: str) -> dict[str, Any] | None:
        return await self.get_section(snapshot_key, "inventory")

    async def get_status(self, snapshot_key: str) -> dict[str, Any] | None:
        return await self.get_section(snapshot_key, "status")

    async def get_source(self, snapshot_key: str) -> dict[str, Any] | None:
        return await self.get_section(snapshot_key, "source")

    async def patch_section(
        self,
        snapshot_key: str,
        section: ActorSnapshotSection,
        data: dict[str, Any],
        ttl: int | None = DEFAULT_TTL_SECONDS,
    ) -> None:
        await self.redis.json_module.set(snapshot_key, f"$.{section}", data)
        if ttl is not None:
            await self.redis.string.expire(snapshot_key, ttl)

    async def touch(self, snapshot_key: str, ttl: int = DEFAULT_TTL_SECONDS) -> bool:
        return await self.redis.string.expire(snapshot_key, ttl)

    async def delete_snapshot(self, snapshot_key: str) -> None:
        await self.redis.string.delete(snapshot_key)

    @staticmethod
    def _first(result: Any) -> dict[str, Any] | None:
        if isinstance(result, list):
            return result[0] if result and isinstance(result[0], dict) else None
        return result if isinstance(result, dict) else None

    @staticmethod
    def _normalize_snapshot(data: dict[str, Any]) -> dict[str, Any]:
        return {
            "meta": data.get("meta") or {},
            "runtime": data.get("runtime") or {},
            "combat": data.get("combat") or {},
            "inventory": data.get("inventory") or {},
            "status": data.get("status") or {},
            "source": data.get("source") or {},
        }
