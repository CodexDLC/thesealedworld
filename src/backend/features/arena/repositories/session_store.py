from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.arena.dto.session import ArenaCombatRequestDTO, ArenaQueueRequestDTO

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService


class ArenaSessionStore:
    REQUEST_TTL_SEC = 300
    MATCH_TTL_SEC = 900

    def __init__(self, redis: RedisService) -> None:
        self.redis = redis

    def _client(self):
        if hasattr(self.redis, "redis_client"):
            return self.redis.redis_client
        return self.redis.pipeline.client

    @staticmethod
    def queue_key(mode: str) -> str:
        return f"arena:queue:{mode}"

    @staticmethod
    def request_key(char_id: int) -> str:
        return f"arena:request:{char_id}"

    @staticmethod
    def match_key(arena_session_id: str) -> str:
        return f"arena:match:{arena_session_id}"

    @staticmethod
    def char_match_key(char_id: int) -> str:
        return f"arena:char_match:{char_id}"

    async def add_to_queue(self, request: ArenaQueueRequestDTO) -> None:
        client = self._client()
        await client.zadd(self.queue_key(request.mode), {str(request.char_id): float(request.gs)})
        await client.set(self.request_key(request.char_id), request.model_dump_json(), ex=self.REQUEST_TTL_SEC)

    async def remove_from_queue(self, mode: str, char_id: int) -> bool:
        removed = await self._client().zrem(self.queue_key(mode), str(char_id))
        return bool(removed)

    async def delete_request(self, char_id: int) -> None:
        await self._client().delete(self.request_key(char_id))

    async def get_request(self, char_id: int) -> ArenaQueueRequestDTO | None:
        raw = await self._client().get(self.request_key(char_id))
        if raw is None:
            return None
        return ArenaQueueRequestDTO.model_validate_json(raw)

    async def get_candidates(self, mode: str, min_gs: float, max_gs: float) -> list[int]:
        values = await self._client().zrangebyscore(self.queue_key(mode), min_gs, max_gs)
        return [int(value) for value in values]

    async def create_match(self, request: ArenaCombatRequestDTO) -> None:
        client = self._client()
        data = request.model_dump_json()
        await client.set(self.match_key(request.arena_session_id), data, ex=self.MATCH_TTL_SEC)
        for participants in request.participants.values():
            for char_id in participants:
                await client.set(self.char_match_key(char_id), request.arena_session_id, ex=self.MATCH_TTL_SEC)

    async def get_match(self, arena_session_id: str) -> ArenaCombatRequestDTO | None:
        raw = await self._client().get(self.match_key(arena_session_id))
        if raw is None:
            return None
        return ArenaCombatRequestDTO.model_validate_json(raw)

    async def get_match_for_char(self, char_id: int) -> ArenaCombatRequestDTO | None:
        arena_session_id = await self._client().get(self.char_match_key(char_id))
        if not arena_session_id:
            return None
        return await self.get_match(str(arena_session_id))

    async def update_match(self, match: ArenaCombatRequestDTO) -> None:
        await self._client().set(self.match_key(match.arena_session_id), match.model_dump_json(), ex=self.MATCH_TTL_SEC)

    async def delete_match(self, match: ArenaCombatRequestDTO) -> None:
        client = self._client()
        keys = [self.match_key(match.arena_session_id)]
        for participants in match.participants.values():
            keys.extend(self.char_match_key(char_id) for char_id in participants)
        await client.delete(*keys)
