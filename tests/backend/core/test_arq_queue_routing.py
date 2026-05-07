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
