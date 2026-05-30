from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.infrastructure.redis.keys import GameSessionLockKey

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService


class GameSessionLockManager:
    """Tracks the single active game session id per character.

    Implements last-login-wins single-session enforcement: the most recent
    ``claim(char_id, session_id)`` overwrites the previous value, and any
    subsequent ``current(char_id)`` returns the new id. Requests carrying a
    stale ``session_id`` in their JWT can be rejected by comparing against
    ``current(char_id)``.

    Backed by a Redis string key ``game:ac_sess:{char_id}`` with the same
    6-hour TTL as ``CharacterSessionManager`` (the runtime AC document) so the
    lock expires together with the playable state it guards.
    """

    DEFAULT_TTL_SECONDS = 6 * 60 * 60

    def __init__(self, redis: RedisService, *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self.redis = redis
        self.key = GameSessionLockKey()
        self.ttl_seconds = ttl_seconds

    def build_key(self, char_id: int) -> str:
        return self.key.build(char_id=char_id)

    async def claim(self, char_id: int, session_id: str) -> None:
        """Set ``session_id`` as the active session for ``char_id`` (last wins)."""
        await self.redis.string.set(self.build_key(char_id), session_id, ttl=self.ttl_seconds)

    async def current(self, char_id: int) -> str | None:
        """Return the currently active session id for ``char_id``, if any."""
        return await self.redis.string.get(self.build_key(char_id))

    async def release(self, char_id: int) -> None:
        """Drop the active session id for ``char_id`` (logout / character release)."""
        await self.redis.string.delete(self.build_key(char_id))

    async def touch(self, char_id: int) -> None:
        """Refresh the TTL of an existing lock without changing its value."""
        await self.redis.string.expire(self.build_key(char_id), self.ttl_seconds)
