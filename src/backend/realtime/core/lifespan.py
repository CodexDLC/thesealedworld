"""Bootstrap helpers for the realtime module.

Stage 1 co-locates the realtime gateway inside the chat container (see
``docs/planning/tech-debt/realtime/player_realtime_gateway.md``). Splitting it
into its own process is deferred to a later stage: chat already owns Redis,
``MessageService``, and the stream runtime, so building a separate container
for stage 1 would be churn without a delivery win.

TODO(stage-2): factor the realtime gateway into its own FastAPI app
(``src/backend/realtime/app.py``) and run it as a dedicated container.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.infrastructure.actor_state.managers import GameSessionLockManager
from src.backend.realtime.services.connection_manager import RealtimeConnectionManager

if TYPE_CHECKING:
    from fastapi import FastAPI


class _StringRedisAdapter:
    """Minimal ``RedisService.string``-shaped wrapper around ``redis.asyncio``.

    :class:`GameSessionLockManager` only uses ``string.get/set/delete/expire``,
    so we expose just those operations rather than dragging the full
    ``codex_platform.redis_service.RedisService`` (and its dependencies) into
    the chat container.
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    async def get(self, key: str) -> str | None:
        return await self._client.get(key)

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        if ttl is None:
            await self._client.set(key, value)
        else:
            await self._client.set(key, value, ex=ttl)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def expire(self, key: str, ttl: int) -> bool:
        return bool(await self._client.expire(key, ttl))


class _RedisServiceAdapter:
    """Carries the ``.string`` surface :class:`GameSessionLockManager` needs."""

    def __init__(self, client: Any) -> None:
        self.string = _StringRedisAdapter(client)


def bootstrap_realtime(app: FastAPI) -> None:
    """Attach realtime singletons to ``app.state``.

    Idempotent — safe to call from the chat container's lifespan after Redis
    is wired up.
    """
    if not hasattr(app.state, "realtime_manager"):
        app.state.realtime_manager = RealtimeConnectionManager()
    if not hasattr(app.state, "game_session_lock"):
        adapter = _RedisServiceAdapter(app.state.redis)
        app.state.game_session_lock = GameSessionLockManager(adapter)  # type: ignore[arg-type]
