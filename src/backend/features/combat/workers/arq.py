# ruff: noqa: E402
from src.backend.core.arq_logging import setup_arq_worker_logging

setup_arq_worker_logging("combat-worker")

from loguru import logger as log

from src.backend.core.arq import COMBAT_ARQ_QUEUE, ArqService, BaseArqSettings, base_shutdown, base_startup
from src.backend.features.combat.integrations import CombatSessionIntegration
from src.backend.features.combat.runtime.processors.ai_processor import AiProcessor
from src.backend.features.combat.runtime.processors.collector import CombatCollector
from src.backend.features.combat.runtime.processors.executor import CombatExecutor
from src.backend.features.combat.services.turn_manager import CombatTurnManager

from .tasks.ai_turn_task import ai_turn_task
from .tasks.chaos_task import chaos_check_task
from .tasks.collector_task import combat_collector_task
from .tasks.executor_task import execute_batch_task
from .tasks.finalization_persist_task import combat_finalization_persist_task
from .tasks.result_support_task import combat_result_support_task
from .tasks.victory_finalizer_task import victory_finalizer_task

COMBAT_RUNTIME_MAX_JOBS = 30

COMBAT_TASKS = [
    combat_collector_task,
    execute_batch_task,
    ai_turn_task,
    chaos_check_task,
    victory_finalizer_task,
    combat_result_support_task,
    combat_finalization_persist_task,
]


async def combat_startup(ctx: dict) -> None:
    """Initialize combat worker dependencies and register runtime processors."""
    log.bind(stage="start", worker_type="combat").info("WorkerInit")
    await base_startup(ctx)
    redis_service = ctx["redis_service"]
    combat_data_service = CombatSessionIntegration.from_redis(redis_service)
    arq_service = ArqService()

    ctx["combat_data_service"] = combat_data_service
    ctx["combat_collector"] = CombatCollector(combat_data_service)
    ctx["combat_executor"] = CombatExecutor()
    ctx["ai_processor"] = AiProcessor()
    ctx["turn_manager"] = CombatTurnManager(combat_data_service, arq_service, ctx.get("game_config"))
    ctx["arq_service"] = arq_service
    log.bind(stage="complete", worker_type="combat").info("WorkerInit")


async def combat_shutdown(ctx: dict) -> None:
    """Close worker-local runtime services during ARQ shutdown."""
    log.bind(stage="start", worker_type="combat").info("WorkerShutdown")
    arq_service = ctx.get("arq_service")
    if arq_service is not None:
        await arq_service.close()
    await base_shutdown(ctx)
    log.bind(stage="complete", worker_type="combat").info("WorkerShutdown")


class CombatArqSettings(BaseArqSettings):
    """ARQ worker settings for the combat runtime queue."""

    redis_settings = BaseArqSettings.redis_settings
    queue_name = COMBAT_ARQ_QUEUE
    max_jobs: int = COMBAT_RUNTIME_MAX_JOBS
    job_timeout: int = 60
    keep_result: int = 0
    on_startup = combat_startup
    on_shutdown = combat_shutdown
    functions = COMBAT_TASKS
