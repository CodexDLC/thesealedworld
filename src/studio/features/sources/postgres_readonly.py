"""Per-source read-only Postgres pool factory.

Holds one `asyncpg.Pool` per `SourceKind` and lazily creates it on first
request. Pools are closed in the FastAPI shutdown handler.

Read-only is enforced on the *database* side via the `studio_ro` role for
prod — even if studio code accidentally calls UPDATE, Postgres rejects it.
For local, callers should still treat connections as read-only by convention.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    import asyncpg

    from src.studio.features.sources.models import Source, SourceKind


class PostgresPoolRegistry:
    """Lazy pool-per-source registry, lifetime-bound to the FastAPI app.

    Lives on `app.state.pg_pools`. Repository code does:

        pool = await app.state.pg_pools.get(request.state.source)
        async with pool.acquire() as conn:
            ...
    """

    def __init__(self) -> None:
        self._pools: dict[SourceKind, asyncpg.Pool] = {}

    async def get(self, source: Source) -> asyncpg.Pool:
        import asyncpg

        existing = self._pools.get(source.kind)
        if existing is not None:
            return existing

        logger.bind(source=source.kind, dsn_host=_host_of(source.pg_dsn)).info("StudioPgPoolCreating")
        pool = await asyncpg.create_pool(
            dsn=source.pg_dsn,
            min_size=1,
            max_size=5,
            command_timeout=30.0,
        )
        self._pools[source.kind] = pool
        return pool

    async def close_all(self) -> None:
        for kind, pool in list(self._pools.items()):
            logger.bind(source=kind).info("StudioPgPoolClosing")
            try:
                await pool.close()
            except Exception:  # noqa: BLE001
                logger.bind(source=kind).opt(exception=True).warning("StudioPgPoolCloseFailed")
            self._pools.pop(kind, None)


def _host_of(dsn: str) -> str:
    """Extract host:port from a Postgres DSN for safe logging."""
    try:
        after_at = dsn.split("@", 1)[1]
        return after_at.split("/", 1)[0]
    except (IndexError, ValueError):
        return "?"
