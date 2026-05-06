from __future__ import annotations

from typing import Any

from loguru import logger

from src.backend.core.arq import BaseArqSettings, base_shutdown, base_startup
from src.backend.features.character.workers.tasks import CHARACTER_TASKS

SYSTEM_TASKS = (*CHARACTER_TASKS,)


async def system_startup(ctx: dict[str, Any]) -> None:
    logger.info("WorkerInit | stage=start worker_type=system")
    await base_startup(ctx)
    logger.info("WorkerInit | stage=complete worker_type=system")


async def system_shutdown(ctx: dict[str, Any]) -> None:
    logger.info("WorkerShutdown | stage=start worker_type=system")
    await base_shutdown(ctx)
    logger.info("WorkerShutdown | stage=complete worker_type=system")


class SystemArqSettings(BaseArqSettings):
    redis_settings = BaseArqSettings.redis_settings
    max_jobs: int = 20
    job_timeout: int = 60
    keep_result: int = 5
    on_startup = system_startup
    on_shutdown = system_shutdown
    functions = SYSTEM_TASKS
