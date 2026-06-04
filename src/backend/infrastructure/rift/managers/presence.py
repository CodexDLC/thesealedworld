from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService


class RiftPresenceStore:
    DEFAULT_TTL_SECONDS = 60 * 60
    KEY_PREFIX = "game:rift:presence:"

    def __init__(self, redis: RedisService, *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self.redis = redis
        self.ttl_seconds = ttl_seconds

    def build_node_key(self, rift_instance_id: str, node_id: str) -> str:
        return f"{self.KEY_PREFIX}{rift_instance_id}:node:{node_id}"

    def build_travel_key(self, rift_instance_id: str, travel_id: str) -> str:
        return f"{self.KEY_PREFIX}{rift_instance_id}:travel:{travel_id}"

    def build_encounter_key(self, rift_instance_id: str, encounter_id: str) -> str:
        return f"{self.KEY_PREFIX}{rift_instance_id}:encounter:{encounter_id}"

    async def enter_node(self, rift_instance_id: str, node_id: str, participant_ref: str) -> None:
        await self._add(self.build_node_key(rift_instance_id, node_id), participant_ref)

    async def leave_node(self, rift_instance_id: str, node_id: str, participant_ref: str) -> None:
        await self._remove(self.build_node_key(rift_instance_id, node_id), participant_ref)

    async def move_node(
        self,
        rift_instance_id: str,
        *,
        from_node_id: str | None,
        to_node_id: str,
        participant_ref: str,
    ) -> None:
        if from_node_id:
            await self.leave_node(rift_instance_id, from_node_id, participant_ref)
        await self.enter_node(rift_instance_id, to_node_id, participant_ref)

    async def get_node_occupants(self, rift_instance_id: str, node_id: str) -> set[str]:
        return await self._members(self.build_node_key(rift_instance_id, node_id))

    async def join_travel(self, rift_instance_id: str, travel_id: str, participant_ref: str) -> None:
        await self._add(self.build_travel_key(rift_instance_id, travel_id), participant_ref)

    async def leave_travel(self, rift_instance_id: str, travel_id: str, participant_ref: str) -> None:
        await self._remove(self.build_travel_key(rift_instance_id, travel_id), participant_ref)

    async def get_travel_participants(self, rift_instance_id: str, travel_id: str) -> set[str]:
        return await self._members(self.build_travel_key(rift_instance_id, travel_id))

    async def join_encounter(self, rift_instance_id: str, encounter_id: str, participant_ref: str) -> None:
        await self._add(self.build_encounter_key(rift_instance_id, encounter_id), participant_ref)

    async def leave_encounter(self, rift_instance_id: str, encounter_id: str, participant_ref: str) -> None:
        await self._remove(self.build_encounter_key(rift_instance_id, encounter_id), participant_ref)

    async def get_encounter_participants(self, rift_instance_id: str, encounter_id: str) -> set[str]:
        return await self._members(self.build_encounter_key(rift_instance_id, encounter_id))

    async def clear_node_presence(self, rift_instance_id: str, node_id: str) -> None:
        await self._delete(self.build_node_key(rift_instance_id, node_id))

    async def clear_travel_presence(self, rift_instance_id: str, travel_id: str) -> None:
        await self._delete(self.build_travel_key(rift_instance_id, travel_id))

    async def clear_encounter_presence(self, rift_instance_id: str, encounter_id: str) -> None:
        await self._delete(self.build_encounter_key(rift_instance_id, encounter_id))

    async def snapshot_instance_presence(
        self, rift_instance_id: str, *, limit: int = 1000
    ) -> dict[str, dict[str, list[str]]]:
        client = self._redis_client()
        cursor = 0
        result: dict[str, dict[str, list[str]]] = {"nodes": {}, "travels": {}, "encounters": {}}
        prefix = f"{self.KEY_PREFIX}{rift_instance_id}:"
        while True:
            cursor, keys = await client.scan(cursor=cursor, match=f"{prefix}*", count=min(limit, 100))
            for raw_key in keys:
                key = self._decode(raw_key)
                section, item_id = self._presence_section_and_id(key, prefix)
                if section is None or item_id is None:
                    continue
                result[section][item_id] = sorted(await self._members(key))
                if sum(len(values) for values in result.values()) >= limit:
                    return result
            if cursor == 0:
                return result

    async def rebuild_node_presence_from_sessions(
        self,
        rift_instance_id: str,
        sessions: dict[str, dict[str, Any]],
    ) -> None:
        for session in sessions.values():
            node_id = str(session.get("current_node_id") or "")
            participant_ref = str(session.get("participant_ref") or session.get("owner_id") or "")
            if node_id and participant_ref:
                await self.enter_node(rift_instance_id, node_id, participant_ref)

    def _redis_client(self) -> Any:
        if hasattr(self.redis, "redis_client"):
            return self.redis.redis_client
        return self.redis.pipeline.client

    async def _add(self, key: str, participant_ref: str) -> None:
        client = self._redis_client()
        await client.sadd(key, participant_ref)
        await client.expire(key, self.ttl_seconds)

    async def _remove(self, key: str, participant_ref: str) -> None:
        await self._redis_client().srem(key, participant_ref)

    async def _members(self, key: str) -> set[str]:
        raw_members = await self._redis_client().smembers(key)
        return {self._decode(member) for member in raw_members}

    async def _delete(self, key: str) -> None:
        client = self._redis_client()
        if hasattr(client, "delete"):
            await client.delete(key)

    @staticmethod
    def _decode(value: Any) -> str:
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)

    @staticmethod
    def _presence_section_and_id(key: str, prefix: str) -> tuple[str | None, str | None]:
        rest = key.removeprefix(prefix)
        raw_section, _, item_id = rest.partition(":")
        section_map = {"node": "nodes", "travel": "travels", "encounter": "encounters"}
        section = section_map.get(raw_section)
        return section, item_id or None
