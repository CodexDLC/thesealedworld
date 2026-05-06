from typing import Any, Literal

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
    """RedisJSON access layer for temporary combat actor commitments.

    Commitments freeze combat-relevant actor input for a feature request, such
    as an arena queue entry. They are temporary and are not source of truth.
    """

    DEFAULT_TTL_SECONDS = 300

    def __init__(self, redis: RedisService) -> None:
        self.redis = redis
        self.key = ActorCommitmentKey()

    def build_key(self, commitment_id: str) -> str:
        return self.key.build(commitment_id=commitment_id)

    def _redis_client(self) -> Any:
        if hasattr(self.redis, "redis_client"):
            return self.redis.redis_client
        return self.redis.pipeline.client

    async def save_commitment(self, commitment_id: str, data: dict[str, Any], ttl: int = DEFAULT_TTL_SECONDS) -> str:
        commitment_key = self.build_key(commitment_id)
        await self.redis.json_module.set(commitment_key, "$", self._normalize_commitment(data))
        await self.redis.string.expire(commitment_key, ttl)
        return commitment_id

    async def save_commitments(
        self,
        commitments: dict[str, dict[str, Any]],
        ttl: int = DEFAULT_TTL_SECONDS,
    ) -> dict[str, str]:
        """Batch-save multiple commitments in one Redis pipeline.

        Returns ``{commitment_id: commitment_id}`` for entries that were written.
        On full pipeline failure returns an empty mapping.
        """
        if not commitments:
            return {}

        ordered_ids = list(commitments.keys())
        keys_by_id = {cid: self.build_key(cid) for cid in ordered_ids}

        try:
            async with self._redis_client().pipeline(transaction=False) as pipe:
                for cid in ordered_ids:
                    key = keys_by_id[cid]
                    normalized = self._normalize_commitment(commitments[cid])
                    pipe.json().set(key, "$", normalized)
                    pipe.expire(key, ttl)
                results = await pipe.execute(raise_on_error=False)
        except Exception:
            return {}

        saved: dict[str, str] = {}
        for index, cid in enumerate(ordered_ids):
            set_result = results[index * 2] if index * 2 < len(results) else None
            expire_result = results[index * 2 + 1] if index * 2 + 1 < len(results) else None
            if isinstance(set_result, Exception) or isinstance(expire_result, Exception):
                continue
            if not set_result:
                continue
            saved[cid] = cid
        return saved

    async def get_commitment(self, commitment_id: str) -> dict[str, Any] | None:
        result = await self.redis.json_module.get(self.build_key(commitment_id), "$")
        return self._first(result)

    async def get_commitments_batch(self, commitment_ids: list[str]) -> dict[str, dict[str, Any] | None]:
        if not commitment_ids:
            return {}

        keys = [self.build_key(commitment_id) for commitment_id in commitment_ids]
        try:
            async with self._redis_client().pipeline(transaction=False) as pipe:
                for key in keys:
                    pipe.json().get(key, "$")
                results = await pipe.execute(raise_on_error=False)
        except Exception:
            return {commitment_id: None for commitment_id in commitment_ids}

        return {
            commitment_id: None if i >= len(results) or isinstance(results[i], Exception) else self._first(results[i])
            for i, commitment_id in enumerate(commitment_ids)
        }

    async def get_section(self, commitment_key: str, section: ActorCommitmentSection) -> dict[str, Any] | None:
        result = await self.redis.json_module.get(commitment_key, f"$.{section}")
        return self._first(result)

    async def get_sections_batch(
        self,
        commitment_keys: list[str],
        section: ActorCommitmentSection,
    ) -> dict[str, dict[str, Any] | None]:
        if not commitment_keys:
            return {}

        path = f"$.{section}"

        try:
            async with self._redis_client().pipeline(transaction=False) as pipe:
                for key in commitment_keys:
                    pipe.json().get(key, path)
                results = await pipe.execute(raise_on_error=False)
        except Exception:
            return {key: None for key in commitment_keys}

        return {
            key: None if i >= len(results) or isinstance(results[i], Exception) else self._first(results[i])
            for i, key in enumerate(commitment_keys)
        }

    async def get_meta(self, commitment_key: str) -> dict[str, Any] | None:
        return await self.get_section(commitment_key, "meta")

    async def get_runtime(self, commitment_key: str) -> dict[str, Any] | None:
        return await self.get_section(commitment_key, "runtime")

    async def get_combat(self, commitment_key: str) -> dict[str, Any] | None:
        return await self.get_section(commitment_key, "combat")

    async def get_inventory(self, commitment_key: str) -> dict[str, Any] | None:
        return await self.get_section(commitment_key, "inventory")

    async def get_status(self, commitment_key: str) -> dict[str, Any] | None:
        return await self.get_section(commitment_key, "status")

    async def get_source(self, commitment_key: str) -> dict[str, Any] | None:
        return await self.get_section(commitment_key, "source")

    async def patch_section(
        self,
        commitment_key: str,
        section: ActorCommitmentSection,
        data: dict[str, Any],
        ttl: int | None = DEFAULT_TTL_SECONDS,
    ) -> None:
        await self.redis.json_module.set(commitment_key, f"$.{section}", data)
        if ttl is not None:
            await self.redis.string.expire(commitment_key, ttl)

    async def touch(self, commitment_key: str, ttl: int = DEFAULT_TTL_SECONDS) -> bool:
        return await self.redis.string.expire(commitment_key, ttl)

    async def delete_commitment(self, commitment_id: str) -> None:
        await self.redis.string.delete(self.build_key(commitment_id))

    @staticmethod
    def _first(result: Any) -> dict[str, Any] | None:
        if isinstance(result, list):
            return result[0] if result and isinstance(result[0], dict) else None
        return result if isinstance(result, dict) else None

    @staticmethod
    def _normalize_commitment(data: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": data.get("schema_version", 1),
            "meta": data.get("meta") or {},
            "runtime": data.get("runtime"),
            "combat": data.get("combat"),
            "inventory": data.get("inventory"),
            "status": data.get("status"),
            "source": data.get("source") or {},
        }
