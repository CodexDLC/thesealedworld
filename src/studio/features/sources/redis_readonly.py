"""Per-source read-only Redis client factory.

Holds one `redis.asyncio.Redis` per `SourceKind`, lazily constructed.
Closed in the FastAPI shutdown handler.

Read-only is by convention here: prod Redis usually has no role-level
ACL for studio, so studio code must restrict itself to `GET` / `HGETALL` /
`XRANGE` / etc. The Source Switcher's red badge is the user-facing reminder.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from src.studio.features.sources.models import Source, SourceKind


class RedisClientRegistry:
    """Lazy client-per-source registry, lifetime-bound to the FastAPI app.

    Lives on `app.state.redis_clients`. Repository code does:

        client = await app.state.redis_clients.get(request.state.source)
        value = await client.get("game:metrics:online")
    """

    def __init__(self) -> None:
        self._clients: dict[SourceKind, Redis] = {}

    async def get(self, source: Source) -> Redis:
        from redis.asyncio import Redis as AsyncRedis

        existing = self._clients.get(source.kind)
        if existing is not None:
            return existing

        logger.bind(source=source.kind, url=source.redis_url).info("StudioRedisClientCreating")
        client = AsyncRedis.from_url(source.redis_url, decode_responses=True)
        self._clients[source.kind] = client
        return client

    async def close_all(self) -> None:
        for kind, client in list(self._clients.items()):
            logger.bind(source=kind).info("StudioRedisClientClosing")
            try:
                await client.aclose()
            except Exception:  # noqa: BLE001
                logger.bind(source=kind).opt(exception=True).warning("StudioRedisClientCloseFailed")
            self._clients.pop(kind, None)
