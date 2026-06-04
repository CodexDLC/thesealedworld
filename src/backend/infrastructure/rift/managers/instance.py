from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.rift.dto import RiftZoneRuntimeDTO

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService


class RiftInstanceNotFoundError(RuntimeError):
    pass


class RiftInstanceStore:
    DEFAULT_TTL_SECONDS = 60 * 60

    def __init__(self, redis: RedisService, *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self.redis = redis
        self.ttl_seconds = ttl_seconds

    def build_instance_key(self, rift_instance_id: str) -> str:
        return f"game:rift:instance:{rift_instance_id}"

    async def save_instance(self, runtime: RiftZoneRuntimeDTO) -> None:
        key = self.build_instance_key(runtime.rift_instance_id)
        await self.redis.json_module.set(key, "$", runtime.model_dump(mode="json"))
        await self.redis.string.expire(key, self.ttl_seconds)

    async def get_instance(self, rift_instance_id: str) -> RiftZoneRuntimeDTO | None:
        result = await self.redis.json_module.get(self.build_instance_key(rift_instance_id), "$")
        doc = self._first(result)
        return RiftZoneRuntimeDTO.model_validate(doc) if isinstance(doc, dict) else None

    async def exists(self, rift_instance_id: str) -> bool:
        return await self.get_instance(rift_instance_id) is not None

    async def require_instance(self, rift_instance_id: str) -> RiftZoneRuntimeDTO:
        runtime = await self.get_instance(rift_instance_id)
        if runtime is None:
            raise RiftInstanceNotFoundError(f"Rift instance not found: {rift_instance_id}")
        return runtime

    async def patch_node_event(self, rift_instance_id: str, node_id: str, event: dict[str, Any]) -> None:
        await self.redis.json_module.set(
            self.build_instance_key(rift_instance_id),
            f"$.node_events.{node_id}",
            event,
        )

    async def mark_node_cleared(self, rift_instance_id: str, node_id: str) -> None:
        await self.redis.json_module.set(
            self.build_instance_key(rift_instance_id),
            f"$.node_states.{node_id}.cleared",
            True,
        )

    async def set_gate_state(self, rift_instance_id: str, gate_key: str, state: dict[str, Any]) -> None:
        await self.redis.json_module.set(
            self.build_instance_key(rift_instance_id),
            f"$.gate_states.{gate_key}",
            state,
        )

    async def set_heart_state(self, rift_instance_id: str, state: dict[str, Any]) -> None:
        await self.redis.json_module.set(self.build_instance_key(rift_instance_id), "$.heart_state", state)

    @staticmethod
    def _first(result: Any) -> Any:
        if isinstance(result, list):
            return result[0] if result else None
        return result
