# ruff: noqa: E402
from __future__ import annotations

from typing import Any

from loguru import logger

from src.backend.core.ai import AIService
from src.backend.core.arq import GENERATION_AI_ARQ_QUEUE, ArqService, BaseArqSettings, base_shutdown, base_startup
from src.backend.core.arq_logging import setup_arq_worker_logging
from src.backend.features.generation_ai.workers.tasks import GENERATION_AI_TASKS

setup_arq_worker_logging("generation-ai-worker")


async def generation_ai_startup(ctx: dict[str, Any]) -> None:
    logger.info("WorkerInit | stage=start worker_type=generation_ai")
    await base_startup(ctx)

    ai = AIService()

    ctx["ai"] = ai
    ctx["generation_ai_arq"] = ArqService(queue_name=GENERATION_AI_ARQ_QUEUE)
    logger.info("WorkerInit | stage=complete worker_type=generation_ai")


async def generation_ai_shutdown(ctx: dict[str, Any]) -> None:
    logger.info("WorkerShutdown | stage=start worker_type=generation_ai")
    arq = ctx.get("generation_ai_arq")
    if arq is not None:
        await arq.close()
    await base_shutdown(ctx)
    logger.info("WorkerShutdown | stage=complete worker_type=generation_ai")


class GenerationAIArqSettings(BaseArqSettings):
    redis_settings = BaseArqSettings.redis_settings
    queue_name = GENERATION_AI_ARQ_QUEUE
    max_jobs: int = 5
    job_timeout: int = 180
    keep_result: int = 30
    on_startup = generation_ai_startup
    on_shutdown = generation_ai_shutdown
    functions = GENERATION_AI_TASKS
