# ruff: noqa: E402
from __future__ import annotations

from typing import Any

from arq import cron
from loguru import logger

from src.backend.core.arq import SYSTEM_ARQ_QUEUE, ArqService, BaseArqSettings, base_shutdown, base_startup
from src.backend.core.arq_logging import setup_arq_worker_logging

setup_arq_worker_logging("system-worker")

from src.backend.features.character.workers.tasks import CHARACTER_TASKS
from src.backend.features.exploration.workers.tasks import EXPLORATION_TASKS
from src.backend.features.inventory.workers.tasks import INVENTORY_TASKS
from src.backend.features.loot.workers.tasks.loot_claim_task import loot_claim_task
from src.backend.features.system.workers.tasks import SYSTEM_COORDINATOR_TASKS, system_dirty_sweeper_task

SYSTEM_TASKS = (*CHARACTER_TASKS, *INVENTORY_TASKS, *EXPLORATION_TASKS, *SYSTEM_COORDINATOR_TASKS, loot_claim_task)
DIRTY_SWEEPER_MINUTES = set(range(0, 60, 3))


async def system_startup(ctx: dict[str, Any]) -> None:
    logger.info("WorkerInit | stage=start worker_type=system")
    await base_startup(ctx)
    ctx["system_arq"] = ArqService(queue_name=SYSTEM_ARQ_QUEUE)
    logger.info("WorkerInit | stage=complete worker_type=system")


async def system_shutdown(ctx: dict[str, Any]) -> None:
    logger.info("WorkerShutdown | stage=start worker_type=system")
    arq = ctx.get("system_arq")
    if arq is not None:
        await arq.close()
    await base_shutdown(ctx)
    logger.info("WorkerShutdown | stage=complete worker_type=system")


class SystemArqSettings(BaseArqSettings):
    redis_settings = BaseArqSettings.redis_settings
    queue_name = SYSTEM_ARQ_QUEUE
    max_jobs: int = 20
    job_timeout: int = 60
    keep_result: int = 5
    on_startup = system_startup
    on_shutdown = system_shutdown
    functions = SYSTEM_TASKS
    cron_jobs = [
        cron(system_dirty_sweeper_task, minute=DIRTY_SWEEPER_MINUTES),
    ]
