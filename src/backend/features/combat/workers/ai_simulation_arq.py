# ruff: noqa: E402
from __future__ import annotations

from src.backend.core.arq_logging import setup_arq_worker_logging

setup_arq_worker_logging("combat-ai-simulation-worker")

from typing import Any

from arq.worker import func
from loguru import logger as log

from src.backend.core.arq import COMBAT_AI_SIMULATION_ARQ_QUEUE, BaseArqSettings, base_shutdown, base_startup
from src.backend.features.combat.workers.tasks.ai_simulation_task import (
    combat_ai_battle_training_task,
    combat_ai_live_simulation_task,
    combat_ai_synthetic_training_task,
)

AI_LIVE_SIMULATION_JOB_TIMEOUT_SECONDS = 180
AI_SYNTHETIC_TRAINING_JOB_TIMEOUT_SECONDS = 900
AI_BATTLE_TRAINING_JOB_TIMEOUT_SECONDS = 2400
COMBAT_AI_SIMULATION_WORKER_MAX_JOBS = 1

COMBAT_AI_SIMULATION_TASKS = [
    func(combat_ai_live_simulation_task, timeout=AI_LIVE_SIMULATION_JOB_TIMEOUT_SECONDS, max_tries=1),
    func(combat_ai_synthetic_training_task, timeout=AI_SYNTHETIC_TRAINING_JOB_TIMEOUT_SECONDS, max_tries=1),
    func(combat_ai_battle_training_task, timeout=AI_BATTLE_TRAINING_JOB_TIMEOUT_SECONDS, max_tries=1),
]


async def combat_ai_simulation_startup(ctx: dict[str, Any]) -> None:
    log.bind(stage="start", worker_type="combat_ai_simulation").info("WorkerInit")
    await base_startup(ctx)
    log.bind(stage="complete", worker_type="combat_ai_simulation").info("WorkerInit")


async def combat_ai_simulation_shutdown(ctx: dict[str, Any]) -> None:
    log.bind(stage="start", worker_type="combat_ai_simulation").info("WorkerShutdown")
    await base_shutdown(ctx)
    log.bind(stage="complete", worker_type="combat_ai_simulation").info("WorkerShutdown")


class CombatAiSimulationArqSettings(BaseArqSettings):
    """ARQ worker settings for admin combat AI simulation and training jobs."""

    redis_settings = BaseArqSettings.redis_settings
    queue_name = COMBAT_AI_SIMULATION_ARQ_QUEUE
    max_jobs: int = COMBAT_AI_SIMULATION_WORKER_MAX_JOBS
    job_timeout: int = AI_BATTLE_TRAINING_JOB_TIMEOUT_SECONDS
    keep_result: int = 0
    on_startup = combat_ai_simulation_startup
    on_shutdown = combat_ai_simulation_shutdown
    functions = COMBAT_AI_SIMULATION_TASKS
