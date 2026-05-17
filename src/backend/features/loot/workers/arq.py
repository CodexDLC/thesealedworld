# ruff: noqa: E402
from src.backend.core.arq_logging import setup_arq_worker_logging

setup_arq_worker_logging("loot-worker")

from loguru import logger as log

from src.backend.core.arq import SYSTEM_ARQ_QUEUE, BaseArqSettings, base_shutdown, base_startup

from .tasks.loot_claim_task import loot_claim_task

LOOT_TASKS = [loot_claim_task]


async def loot_startup(ctx: dict) -> None:
    log.info("WorkerInit | stage=start worker_type=loot")
    await base_startup(ctx)
    log.info("WorkerInit | stage=complete worker_type=loot")


async def loot_shutdown(ctx: dict) -> None:
    log.info("WorkerShutdown | stage=start worker_type=loot")
    await base_shutdown(ctx)
    log.info("WorkerShutdown | stage=complete worker_type=loot")


class LootArqSettings(BaseArqSettings):
    redis_settings = BaseArqSettings.redis_settings
    queue_name = SYSTEM_ARQ_QUEUE
    max_jobs = 20
    job_timeout = 60
    keep_result = 0
    on_startup = loot_startup
    on_shutdown = loot_shutdown
    functions = LOOT_TASKS
