from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from src.backend.infrastructure.arena.schemas.session import ArenaCombatSessionSchema, ArenaQueueSessionSchema

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService

QueueT = TypeVar("QueueT", bound=ArenaQueueSessionSchema)
CombatT = TypeVar("CombatT", bound=ArenaCombatSessionSchema)


class ArenaSessionManager:
    REQUEST_TTL_SEC = 300
    MATCH_TTL_SEC = 900
    MATCH_LOCK_TTL_SEC = 8
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
        queue_schema: type[QueueT] = ArenaQueueSessionSchema,
        combat_schema: type[CombatT] = ArenaCombatSessionSchema,
    ) -> None:
        self.redis = redis
        self.queue_schema = queue_schema
        self.combat_schema = combat_schema

    def _client(self):
        if hasattr(self.redis, "redis_client"):
            return self.redis.redis_client
        return self.redis.pipeline.client

    @staticmethod
    def queue_key(mode: str, mode_size: int = 1) -> str:
        return f"arena:queue:{mode}:{mode_size}"

    @staticmethod
    def request_key(char_id: int) -> str:
        return f"arena:request:{char_id}"

    @staticmethod
    def match_key(arena_session_id: str) -> str:
        return f"arena:match:{arena_session_id}"

    @staticmethod
    def char_match_key(char_id: int) -> str:
        return f"arena:char_match:{char_id}"

    @staticmethod
    def match_lock_key(entity_type: str, entity_id: int) -> str:
        return f"arena:lock:match:{entity_type}:{entity_id}"

    @staticmethod
    def request_key_prefix() -> str:
        return "arena:request:"

    async def add_to_queue(self, request: QueueT) -> None:
        client = self._client()
        score = float(request.gs_locked if request.gs_locked is not None else request.gs)
        await client.zadd(self.queue_key(request.mode, request.mode_size), {str(request.char_id): score})
        await client.set(
            self.request_key(request.char_id),
            request.model_dump_json(),
            ex=max(self.REQUEST_TTL_SEC, request.wait_limit_sec + 60),
        )

    async def remove_from_queue(self, mode: str, char_id: int, *, mode_size: int = 1) -> bool:
        removed = await self._client().zrem(self.queue_key(mode, mode_size), str(char_id))
        return bool(removed)

    async def delete_request(self, char_id: int) -> None:
        await self._client().delete(self.request_key(char_id))

    async def get_request(self, char_id: int) -> QueueT | None:
        raw = await self._client().get(self.request_key(char_id))
        if raw is None:
            return None
        return self.queue_schema.model_validate_json(raw)

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
