# ruff: noqa: E402
from src.backend.core.arq_logging import setup_arq_worker_logging

setup_arq_worker_logging("combat-worker")

from arq.worker import func
from loguru import logger as log

from src.backend.core.arq import COMBAT_ARQ_QUEUE, ArqService, BaseArqSettings, base_shutdown, base_startup
from src.backend.features.combat.integrations import CombatSessionIntegration
from src.backend.features.combat.runtime.processors.ai_processor import AiProcessor
from src.backend.features.combat.runtime.processors.collector import CombatCollector
from src.backend.features.combat.runtime.processors.executor import CombatExecutor
from src.backend.features.combat.services.turn_manager import CombatTurnManager

from .tasks.ai_simulation_task import (
    LIVE_SIMULATION_WORKER_CONCURRENCY,
    combat_ai_battle_training_task,
    combat_ai_live_simulation_task,
    combat_ai_synthetic_training_task,
)
from .tasks.ai_turn_task import ai_turn_task
from .tasks.chaos_task import chaos_check_task
from .tasks.collector_task import combat_collector_task
from .tasks.executor_task import execute_batch_task
from .tasks.finalization_persist_task import combat_finalization_persist_task
from .tasks.result_support_task import combat_result_support_task
from .tasks.victory_finalizer_task import victory_finalizer_task

# DEV load-test value for AI simulation batches. Return live jobs to the
# normal production timeout before enabling this compose profile outside local balance tests.
AI_LIVE_SIMULATION_JOB_TIMEOUT_SECONDS = 180
AI_SYNTHETIC_TRAINING_JOB_TIMEOUT_SECONDS = 900
AI_BATTLE_TRAINING_JOB_TIMEOUT_SECONDS = 2400
# DEV load-test value: keep ARQ claim concurrency aligned with the live simulation
# semaphore, otherwise jobs wait inside the worker and spend their timeout before running.
COMBAT_WORKER_LOADTEST_MAX_JOBS = LIVE_SIMULATION_WORKER_CONCURRENCY

COMBAT_TASKS = [
    combat_collector_task,
    execute_batch_task,
    ai_turn_task,
    func(combat_ai_live_simulation_task, timeout=AI_LIVE_SIMULATION_JOB_TIMEOUT_SECONDS, max_tries=1),
    func(combat_ai_synthetic_training_task, timeout=AI_SYNTHETIC_TRAINING_JOB_TIMEOUT_SECONDS, max_tries=1),
    func(combat_ai_battle_training_task, timeout=AI_BATTLE_TRAINING_JOB_TIMEOUT_SECONDS, max_tries=1),
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
    # DEV load-test override for 100x admin AI battle batches; restore before prod deploy.
    max_jobs: int = COMBAT_WORKER_LOADTEST_MAX_JOBS
    # DEV load-test override for 100x admin AI battle batches; restore before prod deploy.
    job_timeout: int = AI_BATTLE_TRAINING_JOB_TIMEOUT_SECONDS
    keep_result: int = 0
    on_startup = combat_startup
    on_shutdown = combat_shutdown
    functions = COMBAT_TASKS
