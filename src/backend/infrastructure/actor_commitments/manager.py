from typing import Any, Literal
from uuid import NAMESPACE_URL, uuid5

from codex_platform.redis_service import RedisService

from src.backend.infrastructure.redis.keys import ActorCommitmentKey

ActorCommitmentSection = Literal["meta", "runtime", "combat", "inventory", "status", "source"]

META: ActorCommitmentSection = "meta"
RUNTIME: ActorCommitmentSection = "runtime"
COMBAT: ActorCommitmentSection = "combat"
INVENTORY: ActorCommitmentSection = "inventory"
STATUS: ActorCommitmentSection = "status"
SOURCE: ActorCommitmentSection = "source"

ALL_SECTIONS: set[ActorCommitmentSection] = {META, RUNTIME, COMBAT, INVENTORY, STATUS, SOURCE}
ALWAYS_SECTIONS: set[ActorCommitmentSection] = {META, SOURCE}


def resolve_sections(include: set[str] | None, exclude: set[str]) -> set[ActorCommitmentSection]:
    selected: set[str] = set(ALL_SECTIONS)
    if include is not None:
        selected &= include
    selected -= exclude
    selected |= ALWAYS_SECTIONS
    return {section for section in selected if section in ALL_SECTIONS}


class ActorCommitmentManager:
    """RedisJSON access layer for temporary combat actor snapshots.

    Actor snapshots freeze combat-relevant actor input for a feature request,
    such as an arena queue entry. They are temporary and are not source of truth.
    """

    DEFAULT_TTL_SECONDS = 300

    def __init__(self, redis: RedisService) -> None:
        self.redis = redis
        self.key = ActorCommitmentKey()

    @staticmethod
    def source_ref(actor_type: Literal["player", "monster"], source_id: int | str) -> str:
        return f"{actor_type}:{source_id}"

    @staticmethod
    def actor_uuid(scope_id: str, actor_type: Literal["player", "monster"], source_id: int | str) -> str:
        return str(uuid5(NAMESPACE_URL, f"combat-actor:{scope_id}:{actor_type}:{source_id}"))

    def build_key(self, scope_id: str, actor_id: str) -> str:
        return self.key.build(scope_id=scope_id, actor_id=actor_id)

    def _redis_client(self) -> Any:
        if hasattr(self.redis, "redis_client"):
            return self.redis.redis_client
        return self.redis.pipeline.client

    async def save_snapshot(
        self,
        scope_id: str,
        actor_id: str,
        data: dict[str, Any],
        ttl: int = DEFAULT_TTL_SECONDS,
    ) -> str:
        actor_key = self.build_key(scope_id, actor_id)
        await self.redis.json_module.set(actor_key, "$", self._normalize_commitment(data, actor_id=actor_id))
        await self.redis.string.expire(actor_key, ttl)
        return actor_id

    async def save_snapshots(
        self,
        scope_id: str,
        snapshots: dict[str, dict[str, Any]],
        ttl: int = DEFAULT_TTL_SECONDS,
    ) -> dict[str, str]:
        """Batch-save multiple actor snapshots in one Redis pipeline.

        Returns ``{actor_id: actor_id}`` for entries that were written.
        On full pipeline failure returns an empty mapping.
        """
        if not snapshots:
            return {}

        ordered_ids = list(snapshots.keys())
        keys_by_id = {actor_id: self.build_key(scope_id, actor_id) for actor_id in ordered_ids}

        try:
            async with self._redis_client().pipeline(transaction=False) as pipe:
                for actor_id in ordered_ids:
                    key = keys_by_id[actor_id]
                    normalized = self._normalize_commitment(snapshots[actor_id], actor_id=actor_id)
                    pipe.json().set(key, "$", normalized)
                    pipe.expire(key, ttl)
                results = await pipe.execute(raise_on_error=False)
        except Exception:
            return {}

        saved: dict[str, str] = {}
        for index, actor_id in enumerate(ordered_ids):
            set_result = results[index * 2] if index * 2 < len(results) else None
            expire_result = results[index * 2 + 1] if index * 2 + 1 < len(results) else None
            if isinstance(set_result, Exception) or isinstance(expire_result, Exception):
                continue
            if not set_result:
                continue
            saved[actor_id] = actor_id
        return saved

    async def get_snapshot(self, scope_id: str, actor_id: str) -> dict[str, Any] | None:
        result = await self.redis.json_module.get(self.build_key(scope_id, actor_id), "$")
        return self._first(result)

    async def get_snapshots_batch(self, scope_id: str, actor_ids: list[str]) -> dict[str, dict[str, Any] | None]:
        if not actor_ids:
            return {}

        keys = [self.build_key(scope_id, actor_id) for actor_id in actor_ids]
        try:
            async with self._redis_client().pipeline(transaction=False) as pipe:
                for key in keys:
                    pipe.json().get(key, "$")
                results = await pipe.execute(raise_on_error=False)
        except Exception:
            return {actor_id: None for actor_id in actor_ids}

        return {
            actor_id: None if i >= len(results) or isinstance(results[i], Exception) else self._first(results[i])
            for i, actor_id in enumerate(actor_ids)
        }

    async def get_section(self, scope_id: str, actor_id: str, section: ActorCommitmentSection) -> dict[str, Any] | None:
        result = await self.redis.json_module.get(self.build_key(scope_id, actor_id), f"$.{section}")
        return self._first(result)

    async def get_sections_batch(
        self,
        scope_id: str,
        actor_ids: list[str],
        section: ActorCommitmentSection,
    ) -> dict[str, dict[str, Any] | None]:
        if not actor_ids:
            return {}

        path = f"$.{section}"
        keys = [self.build_key(scope_id, actor_id) for actor_id in actor_ids]

        try:
            async with self._redis_client().pipeline(transaction=False) as pipe:
                for key in keys:
                    pipe.json().get(key, path)
                results = await pipe.execute(raise_on_error=False)
        except Exception:
            return {actor_id: None for actor_id in actor_ids}

        return {
            actor_id: None if i >= len(results) or isinstance(results[i], Exception) else self._first(results[i])
            for i, actor_id in enumerate(actor_ids)
        }

    async def get_meta(self, scope_id: str, actor_id: str) -> dict[str, Any] | None:
        return await self.get_section(scope_id, actor_id, "meta")

    async def get_runtime(self, scope_id: str, actor_id: str) -> dict[str, Any] | None:
        return await self.get_section(scope_id, actor_id, "runtime")

    async def get_combat(self, scope_id: str, actor_id: str) -> dict[str, Any] | None:
        return await self.get_section(scope_id, actor_id, "combat")

    async def get_inventory(self, scope_id: str, actor_id: str) -> dict[str, Any] | None:
        return await self.get_section(scope_id, actor_id, "inventory")

    async def get_status(self, scope_id: str, actor_id: str) -> dict[str, Any] | None:
        return await self.get_section(scope_id, actor_id, "status")

    async def get_source(self, scope_id: str, actor_id: str) -> dict[str, Any] | None:
        return await self.get_section(scope_id, actor_id, "source")

    async def patch_section(
        self,
        scope_id: str,
        actor_id: str,
        section: ActorCommitmentSection,
        data: dict[str, Any],
        ttl: int | None = DEFAULT_TTL_SECONDS,
    ) -> None:
        await self.redis.json_module.set(self.build_key(scope_id, actor_id), f"$.{section}", data)
        if ttl is not None:
            await self.redis.string.expire(self.build_key(scope_id, actor_id), ttl)

    async def touch(self, scope_id: str, actor_id: str, ttl: int = DEFAULT_TTL_SECONDS) -> bool:
        return await self.redis.string.expire(self.build_key(scope_id, actor_id), ttl)

    async def delete_snapshot(self, scope_id: str, actor_id: str) -> None:
        await self.redis.string.delete(self.build_key(scope_id, actor_id))

    @staticmethod
    def _first(result: Any) -> dict[str, Any] | None:
        if isinstance(result, list):
            return result[0] if result and isinstance(result[0], dict) else None
        return result if isinstance(result, dict) else None

    @staticmethod
    def _normalize_commitment(data: dict[str, Any], *, actor_id: str | None = None) -> dict[str, Any]:
        return {
            "schema_version": data.get("schema_version", 1),
            "actor_id": actor_id or data.get("actor_id"),
            "meta": data.get("meta") or {},
            "runtime": data.get("runtime"),
            "combat": data.get("combat"),
            "inventory": data.get("inventory"),
            "status": data.get("status"),
            "source": data.get("source") or {},
        }
