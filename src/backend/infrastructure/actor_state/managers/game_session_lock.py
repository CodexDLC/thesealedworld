from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.config.settings import settings
from src.backend.infrastructure.redis.keys import GameSessionLockKey

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService


def _default_ttl_seconds() -> int:
    # Lock must outlive the refresh token, otherwise an active player whose
    # access token expires mid-session can't refresh: the lock would be gone
    # and the refresh endpoint would treat the slot as released, kicking the
    # player to the lobby even though no one else claimed it.
    return max(60, int(settings.game_refresh_token_expire_minutes) * 60)


class GameSessionLockManager:
    """Tracks the single active game session id per character.

    Implements last-login-wins single-session enforcement: the most recent
    ``claim(char_id, session_id)`` overwrites the previous value, and any
    subsequent ``current(char_id)`` returns the new id. Requests carrying a
    stale ``session_id`` in their JWT can be rejected by comparing against
    ``current(char_id)``.

    Backed by a Redis string key ``game:ac_sess:{char_id}`` whose TTL is
    aligned with ``settings.game_refresh_token_expire_minutes`` so the lock
    stays alive as long as the refresh token can mint new access tokens.
    The refresh endpoint must call :meth:`touch` (or re-``claim``) on every
    successful refresh to keep the TTL rolling forward for active players.
    """

    def __init__(self, redis: RedisService, *, ttl_seconds: int | None = None) -> None:
        self.redis = redis
        self.key = GameSessionLockKey()
        self.ttl_seconds = ttl_seconds if ttl_seconds is not None else _default_ttl_seconds()

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
