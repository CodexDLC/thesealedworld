from __future__ import annotations

import logging
from typing import Any

from loguru import logger

from src.backend.config.settings import settings
from src.backend.core.arq_container import ArqWorkerContainer

COMBAT_ARQ_QUEUE = "tbmmorpg:arq:combat"
COMBAT_AI_SIMULATION_ARQ_QUEUE = "tbmmorpg:arq:combat_ai_simulation"
SYSTEM_ARQ_QUEUE = "tbmmorpg:arq:system"
GENERATION_AI_ARQ_QUEUE = "tbmmorpg:arq:generation_ai"
WARNING = 30
ARQ_JOB_KEY_PREFIXES = ("arq:job:", "arq:retry:", "arq:in-progress:")

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
    _quiet_arq_lifecycle_logs()
    await platform_base_startup(ctx)
    _quiet_arq_lifecycle_logs()
    container = ArqWorkerContainer()
    await container.bootstrap(ctx)
    logger.info("ArqWorkerBaseContextInitialized")


async def base_shutdown(ctx: dict[str, Any]) -> None:
    container = ctx.get("worker_container")
    if container is not None:
        await container.shutdown(ctx)
    await platform_base_shutdown(ctx)


class BaseArqSettings(PlatformArqWorkerSettings):
    redis_settings = _redis_settings() if RedisSettings is not None else None
    max_jobs = 20
    job_timeout = 60
    keep_result = 5
    on_startup = base_startup
    on_shutdown = base_shutdown


def _quiet_arq_lifecycle_logs() -> None:
    for name in ("arq", "arq.worker", "arq.connections", "arq.jobs", "arq.utils"):
        logging.getLogger(name).setLevel(WARNING)


class ArqService(PlatformArqService):
    def __init__(self, queue_name: str = COMBAT_ARQ_QUEUE) -> None:
        if BaseArqSettings.redis_settings is None:
            raise RuntimeError("arq is not installed; cannot enqueue worker jobs")
        self.queue_name = queue_name
        super().__init__(BaseArqSettings.redis_settings)

    async def init(self) -> None:
        if create_pool is None:
            raise RuntimeError("arq is not installed; cannot create ARQ pool")
        if not self.pool:
            self.pool = await create_pool(BaseArqSettings.redis_settings, default_queue_name=self.queue_name)


async def get_arq_pool() -> ArqRedis:
    if create_pool is None:
        raise RuntimeError("arq is not installed; cannot create ARQ pool")
    return await create_pool(BaseArqSettings.redis_settings)


async def clear_arq_queue(redis_client: Any | None, queue_name: str) -> int:
    """Delete one ARQ queue and the job bookkeeping keys referenced by it."""
    if redis_client is None:
        return 0
    raw_job_ids = await redis_client.zrange(queue_name, 0, -1)
    job_ids = [str(job_id) for job_id in raw_job_ids if job_id]
    keys = [queue_name]
    for job_id in job_ids:
        keys.extend(f"{prefix}{job_id}" for prefix in ARQ_JOB_KEY_PREFIXES)
    return int(await redis_client.delete(*keys)) if keys else 0
