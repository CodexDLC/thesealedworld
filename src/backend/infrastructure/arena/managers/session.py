from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, Self

from src.backend.infrastructure.arena.schemas.session import (
    ArenaCombatSessionSchema,
    ArenaQueueSessionSchema,
    ArenaRuntimeSessionSchema,
)

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService


class ModelJsonPayload(Protocol):
    def model_dump_json(self, *args: Any, **kwargs: Any) -> str: ...

    @classmethod
    def model_validate_json(cls, json_data: str | bytes | bytearray, *args: Any, **kwargs: Any) -> Self: ...


class QueueSessionPayload(ModelJsonPayload, Protocol):
    char_id: int
    gs: int
    wait_limit_sec: int


class CombatSessionPayload(ModelJsonPayload, Protocol):
    arena_session_id: str
    participants: dict[str, list[int]]


class RuntimeSessionPayload(ModelJsonPayload, Protocol):
    arena_id: str


class ArenaSessionManager[
    QueueT: QueueSessionPayload,
    CombatT: CombatSessionPayload,
    RuntimeT: RuntimeSessionPayload,
]:
    REQUEST_TTL_SEC = 300
    MATCH_TTL_SEC = 900
    MATCH_LOCK_TTL_SEC = 8
    RUNTIME_TTL_SEC = 6 * 60 * 60
    CLAIM_OPPONENT_SCRIPT = """
local queue_key = KEYS[1]
local request_prefix = ARGV[4]
local candidates = redis.call('ZRANGEBYSCORE', queue_key, ARGV[1], ARGV[2])
for _, candidate in ipairs(candidates) do
    if candidate ~= ARGV[3] then
        local candidate_request = redis.call('GET', request_prefix .. candidate)
        if candidate_request then
            local removed = redis.call('ZREM', queue_key, candidate)
            if removed == 1 then
                redis.call('ZREM', queue_key, ARGV[3])
                return candidate
            end
        else
            redis.call('ZREM', queue_key, candidate)
        end
    end
end
return nil
"""
    RELEASE_LOCK_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
"""

    def __init__(
        self,
        redis: RedisService,
        *,
        queue_schema: type[QueueT] = ArenaQueueSessionSchema,  # type: ignore[assignment]
        combat_schema: type[CombatT] = ArenaCombatSessionSchema,  # type: ignore[assignment]
        runtime_schema: type[RuntimeT] = ArenaRuntimeSessionSchema,  # type: ignore[assignment]
    ) -> None:
        self.redis = redis
        self.queue_schema = queue_schema
        self.combat_schema = combat_schema
        self.runtime_schema = runtime_schema

    def _client(self):
        if hasattr(self.redis, "redis_client"):
            return self.redis.redis_client
        return self.redis.pipeline.client

    def queue_key(self, mode: str, size: int) -> str:
        return f"arena:q:{mode}:{size}"

    def request_key(self, char_id: int) -> str:
        return f"arena:req:{char_id}"

    def request_key_prefix(self) -> str:
        return "arena:req:"

    def match_key(self, session_id: str) -> str:
        return f"arena:m:{session_id}"

    def char_match_key(self, char_id: int) -> str:
        return f"arena:cm:{char_id}"

    def match_lock_key(self, entity_type: str, entity_id: int) -> str:
        return f"arena:lock:{entity_type}:{entity_id}"

    def runtime_key(self, arena_id: str) -> str:
        return f"arena:runtime_session:{arena_id}"

    async def add_to_queue(self, mode: str, request: QueueT, *, mode_size: int = 1) -> None:
        client = self._client()
        await client.zadd(self.queue_key(mode, mode_size), {str(request.char_id): float(request.gs)})
        await client.set(
            self.request_key(request.char_id),
            request.model_dump_json(),
            ex=max(self.REQUEST_TTL_SEC, request.wait_limit_sec + 60),
        )

    async def remove_from_queue(self, mode: str, char_id: int, *, mode_size: int = 1) -> bool:
        removed = await self._client().zrem(self.queue_key(mode, mode_size), str(char_id))
        return bool(removed)

    async def queue_waiting_count(self, mode: str, *, mode_size: int = 1) -> int:
        return int(await self._client().zcard(self.queue_key(mode, mode_size)))

    async def delete_request(self, char_id: int) -> None:
        await self._client().delete(self.request_key(char_id))

    async def get_request(self, char_id: int) -> QueueT | None:
        raw = await self._client().get(self.request_key(char_id))
        if raw is None:
            return None
        return self.queue_schema.model_validate_json(raw)

    async def get_candidates(self, mode: str, min_gs: float, max_gs: float, *, mode_size: int = 1) -> list[int]:
        values = await self._client().zrangebyscore(self.queue_key(mode, mode_size), min_gs, max_gs)
        return [int(value) for value in values]

    async def claim_opponent(
        self, mode: str, char_id: int, min_gs: float, max_gs: float, *, mode_size: int = 1
    ) -> int | None:
        value = await self._client().eval(
            self.CLAIM_OPPONENT_SCRIPT,
            1,
            self.queue_key(mode, mode_size),
            min_gs,
            max_gs,
            str(char_id),
            self.request_key_prefix(),
        )
        return int(value) if value not in (None, "") else None

    async def acquire_match_lock(self, entity_type: str, entity_id: int, token: str) -> bool:
        return bool(
            await self._client().set(
                self.match_lock_key(entity_type, entity_id),
                token,
                ex=self.MATCH_LOCK_TTL_SEC,
                nx=True,
            )
        )

    async def release_match_lock(self, entity_type: str, entity_id: int, token: str) -> None:
        await self._client().eval(self.RELEASE_LOCK_SCRIPT, 1, self.match_lock_key(entity_type, entity_id), token)

    async def create_match(self, request: CombatT) -> None:
        client = self._client()
        data = request.model_dump_json()
        await client.set(self.match_key(request.arena_session_id), data, ex=self.MATCH_TTL_SEC)
        for participants in request.participants.values():
            for char_id in participants:
                await client.set(self.char_match_key(char_id), request.arena_session_id, ex=self.MATCH_TTL_SEC)

    async def get_match(self, arena_session_id: str) -> CombatT | None:
        raw = await self._client().get(self.match_key(arena_session_id))
        if raw is None:
            return None
        return self.combat_schema.model_validate_json(raw)

    async def get_match_for_char(self, char_id: int) -> CombatT | None:
        arena_session_id = await self._client().get(self.char_match_key(char_id))
        if not arena_session_id:
            return None
        return await self.get_match(str(arena_session_id))

    async def update_match(self, match: CombatT) -> None:
        await self._client().set(self.match_key(match.arena_session_id), match.model_dump_json(), ex=self.MATCH_TTL_SEC)

    async def delete_match(self, match: CombatT) -> None:
        client = self._client()
        keys = [self.match_key(match.arena_session_id)]
        for participants in match.participants.values():
            keys.extend(self.char_match_key(char_id) for char_id in participants)
        await client.delete(*keys)

    async def create_runtime_session(self, session: RuntimeT) -> None:
        await self._client().set(
            self.runtime_key(session.arena_id),
            session.model_dump_json(),
            ex=self.RUNTIME_TTL_SEC,
        )

    async def get_runtime_session(self, arena_id: str) -> RuntimeT | None:
        raw = await self._client().get(self.runtime_key(arena_id))
        if raw is None:
            return None
        return self.runtime_schema.model_validate_json(raw)

    async def update_runtime_session(self, session: RuntimeT) -> None:
        await self._client().set(
            self.runtime_key(session.arena_id),
            session.model_dump_json(),
            ex=self.RUNTIME_TTL_SEC,
        )

    async def delete_runtime_session(self, arena_id: str) -> None:
        await self._client().delete(self.runtime_key(arena_id))
