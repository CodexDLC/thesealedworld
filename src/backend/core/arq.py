from __future__ import annotations

from typing import Any

from codex_platform.redis_service import RedisService
from loguru import logger
from redis.asyncio import Redis

from src.backend.config.settings import settings

try:  # pragma: no cover - exercised only when the optional worker runtime is installed.
    from arq.connections import ArqRedis, RedisSettings, create_pool
    from codex_platform.workers.arq import (
        BaseArqService as PlatformArqService,
    )
    from codex_platform.workers.arq import (
        BaseArqWorkerSettings as PlatformArqWorkerSettings,
    )
    from codex_platform.workers.arq import (
        base_shutdown as platform_base_shutdown,
    )
    from codex_platform.workers.arq import (
        base_startup as platform_base_startup,
    )
except ImportError:  # pragma: no cover
    class PlatformArqService:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None: ...

    class PlatformArqWorkerSettings:  # type: ignore[no-redef]
        max_jobs = 20
        job_timeout = 60
        keep_result = 60

    async def platform_base_startup(ctx: dict[str, Any]) -> None:
        return None

    async def platform_base_shutdown(ctx: dict[str, Any]) -> None:
        return None

    class ArqRedis:  # type: ignore[no-redef]
        pass

    class RedisSettings:  # type: ignore[no-redef]
        @classmethod
        def from_dsn(cls, dsn: str) -> Any: ...

    create_pool: Any = None  # type: ignore[no-redef]


def _redis_settings() -> Any:
    if RedisSettings is None:
        raise RuntimeError("arq is not installed; add the arq dependency before starting combat workers")
    return RedisSettings.from_dsn(settings.effective_redis_url)


async def base_startup(ctx: dict[str, Any]) -> None:
    await platform_base_startup(ctx)
    redis_client = Redis.from_url(settings.effective_redis_url, decode_responses=True)
    ctx["redis_client_internal"] = redis_client
    ctx["redis_service"] = RedisService(redis_client)
    logger.info("ARQ worker Redis client initialized")


async def base_shutdown(ctx: dict[str, Any]) -> None:
    client = ctx.get("redis_client_internal")
    if client is not None:
        await client.aclose()
        logger.info("ARQ worker Redis client closed")
    await platform_base_shutdown(ctx)


class BaseArqSettings(PlatformArqWorkerSettings):
    redis_settings = _redis_settings() if RedisSettings is not None else None
    max_jobs = 20
    job_timeout = 60
    keep_result = 5
    on_startup = base_startup
    on_shutdown = base_shutdown


class ArqService(PlatformArqService):
    def __init__(self) -> None:
        if BaseArqSettings.redis_settings is None:
            raise RuntimeError("arq is not installed; cannot enqueue worker jobs")
        super().__init__(BaseArqSettings.redis_settings)


async def get_arq_pool() -> ArqRedis:
    if create_pool is None:
        raise RuntimeError("arq is not installed; cannot create ARQ pool")
    return await create_pool(BaseArqSettings.redis_settings)
