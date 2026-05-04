from loguru import logger as log

from src.backend.core.base_arq import ArqService, BaseArqSettings, base_shutdown, base_startup
from src.backend.database.redis.manager.combat_manager import CombatManager
from src.backend.domains.user_features.combat.combat_engine.combat_data_service import CombatDataService
from src.backend.domains.user_features.combat.combat_engine.processors.ai_processor import AiProcessor
from src.backend.domains.user_features.combat.combat_engine.processors.collector import CombatCollector
from src.backend.domains.user_features.combat.combat_engine.processors.executor import CombatExecutor
from src.backend.domains.user_features.combat.orchestrators.handler.runtime.combat_turn_manager import CombatTurnManager

# Импорты тасок
from .tasks.ai_turn_task import ai_turn_task
from .tasks.chaos_task import chaos_check_task
from .tasks.collector_task import combat_collector_task
from .tasks.executor_task import execute_batch_task
from .tasks.victory_finalizer_task import victory_finalizer_task


async def combat_startup(ctx: dict) -> None:
    """
    Выполняет инициализацию контекста боевого воркера (ARQ).

    Настраивает подключение к Redis, инициализирует сервисы данных,
    процессоры (Executor, Collector, AI) и менеджер ходов.

    Args:
        ctx: Словарь контекста ARQ, передаваемый между задачами.
    """
    log.info("WorkerInit | stage=start worker_type=combat")

    # 1. Базовая инициализация (Redis)
    await base_startup(ctx)

    # 2. Инициализация боевых сервисов
    redis_service = ctx["redis_service"]

    combat_manager = CombatManager(redis_service)
    data_service = CombatDataService(combat_manager)

    # ArqService для TurnManager (внутренняя очередь)
    arq_service = ArqService()

    # 3. Инициализация менеджеров
    turn_manager = CombatTurnManager(combat_manager, arq_service)

    # 4. Инициализация процессоров и внедрение в контекст
    ctx["combat_data_service"] = data_service
    ctx["combat_collector"] = CombatCollector(data_service)
    ctx["combat_executor"] = CombatExecutor()
    ctx["ai_processor"] = AiProcessor()

    ctx["turn_manager"] = turn_manager
    ctx["arq_service_internal"] = arq_service

    log.info("WorkerInit | stage=complete services_loaded=true")


async def combat_shutdown(ctx: dict) -> None:
    """
    Выполняет корректное завершение работы воркера.

    Закрывает соединения с Redis и внутренними пулами.
    """
    log.info("WorkerShutdown | stage=start")

    if "arq_service_internal" in ctx:
        await ctx["arq_service_internal"].close()

    await base_shutdown(ctx)

    log.info("WorkerShutdown | stage=complete")


class CombatArqSettings(BaseArqSettings):
    """
    Конфигурация воркера ARQ для боевой системы.

    Attributes:
        max_jobs (int): Лимит одновременных задач (высокий для concurrency).
        job_timeout (int): Жесткий таймаут выполнения задачи.
    """

    max_jobs: int = 50
    job_timeout: int = 30
    keep_result: int = 0  # Результаты не храним, экономим Redis

    # Регистрация функций-задач
    functions = [
        combat_collector_task,
        execute_batch_task,
        ai_turn_task,
        chaos_check_task,
        victory_finalizer_task,
    ]
