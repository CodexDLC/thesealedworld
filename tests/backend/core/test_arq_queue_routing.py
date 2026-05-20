from __future__ import annotations

from src.backend.core.arq import COMBAT_ARQ_QUEUE, SYSTEM_ARQ_QUEUE, ArqService
from src.backend.features.combat.workers.arq import CombatArqSettings
from src.backend.features.system.workers.arq import SystemArqSettings


def test_worker_settings_use_separate_arq_queues() -> None:
    assert CombatArqSettings.queue_name == COMBAT_ARQ_QUEUE
    assert SystemArqSettings.queue_name == SYSTEM_ARQ_QUEUE
    assert CombatArqSettings.queue_name != SystemArqSettings.queue_name


def test_arq_service_defaults_to_combat_queue() -> None:
    assert ArqService().queue_name == COMBAT_ARQ_QUEUE


def test_arq_service_can_target_system_queue() -> None:
    assert ArqService(queue_name=SYSTEM_ARQ_QUEUE).queue_name == SYSTEM_ARQ_QUEUE


def test_system_worker_consumes_loot_claim_jobs_from_system_queue() -> None:
    function_names = {function.__name__ for function in SystemArqSettings.functions}

    assert "loot_claim_task" in function_names


def test_system_worker_schedules_system_dirty_sweeper() -> None:
    cron_jobs = getattr(SystemArqSettings, "cron_jobs", [])
    sweeper_jobs = [job for job in cron_jobs if job.coroutine.__name__ == "system_dirty_sweeper_task"]

    assert len(sweeper_jobs) == 1
    assert sweeper_jobs[0].minute == set(range(0, 60, 3))


def test_system_worker_consumes_exploration_knowledge_flush_jobs() -> None:
    function_names = {function.__name__ for function in SystemArqSettings.functions}

    assert "flush_exploration_knowledge_task" in function_names
