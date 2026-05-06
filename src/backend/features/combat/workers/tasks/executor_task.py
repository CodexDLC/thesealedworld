import contextlib
import time

from loguru import logger as log

from src.backend.features.combat.dto.action import CombatActionDTO
from src.backend.features.combat.dto.worker import CollectorSignalDTO, WorkerBatchJobDTO
from src.backend.features.combat.runtime.processors.executor import CombatExecutor  # noqa: TC001
from src.backend.features.combat.runtime.services.data_service import CombatDataService  # noqa: TC001


async def execute_batch_task(ctx: dict, job_data: dict) -> None:
    """
    Выполняет пакетную обработку действий (Batch Processing).

    Жизненный цикл:
    1. Загрузка контекста боя (Snapshot).
    2. Блокировка сессии (Distributed Lock).
    3. Выборка действий из очереди Redis.
    4. Расчет логики (Executor).
    5. Коммит состояния (Save Snapshot).
    6. Сигнал коллектору (Heartbeat).

    Args:
        ctx: Контекст ARQ.
        job_data: Данные задачи (WorkerBatchJobDTO).
    """
    session_id = "unknown"
    try:
        job = WorkerBatchJobDTO(**job_data)
        session_id = job.session_id
        my_id = f"worker_{int(time.time() * 1000)}"  # Уникальный ID текущего исполнения

        # 0. Извлечение сервисов
        executor: CombatExecutor = ctx["combat_executor"]
        data_service: CombatDataService | None = ctx.get("combat_data_service")

        if not data_service:
            # Fallback для надежности (если инициализация сбойнула)
            if "combat_collector" in ctx:
                data_service = ctx["combat_collector"].data_service
            else:
                log.error("ExecutorFail | reason=service_not_found")
                return

        # 1. Load Context (Heavy IO)
        battle_ctx = await data_service.load_battle_context(session_id)

        if not battle_ctx or not battle_ctx.meta.active:
            log.warning("ExecutorSkip | reason=inactive_session", session_id=session_id)
            # Снимаем зависшие блокировки, если есть
            if data_service:
                await data_service.combat_manager.release_worker_lock_safe(session_id, "force")
            return

        # 2. Acquire Worker Lock (Concurrency Check)
        # Гарантирует, что только один executor пишет в базу для этой сессии
        acquired = await data_service.combat_manager.acquire_worker_lock(session_id, my_id)
        if not acquired:
            log.warning("ExecutorSkip | reason=locked_by_other", session_id=session_id)
            return

        try:
            # 3. Fetch Actions from Redis Queue
            # Берем пачку действий
            raw_actions = await data_service.load_actions_batch(session_id, job.batch_size)

            if not raw_actions:
                log.info("ExecutorEmpty | session_id={session_id}")
                return

            actions = []
            for raw in raw_actions:
                with contextlib.suppress(Exception):
                    # Валидируем JSON, битые пакеты игнорируем
                    actions.append(CombatActionDTO.model_validate_json(raw))

            # 4. Process Batch (Pure Logic Calculation)
            # Вся математика происходит тут
            processed_ids = await executor.process_batch(battle_ctx, actions)

            # 5. Commit (Zombie Check & Save)
            # Перед записью проверяем, не истек ли наш лок пока мы считали
            is_mine = await data_service.combat_manager.check_worker_lock(session_id, my_id)

            if not is_mine:
                log.error("ExecutorZombie | error=lock_lost_during_calc", session_id=session_id)
                return

            # 5.1. АТОМАРНЫЙ Save (state + logs + actions + targets)
            await data_service.commit_session(battle_ctx, processed_ids)

            log.info(
                "ExecutorSuccess | session_id={session_id} processed={count}",
                session_id=session_id,
                count=len(processed_ids),
            )

        finally:
            # 6. Release Lock
            await data_service.combat_manager.release_worker_lock_safe(session_id, my_id)

            # 7. Heartbeat Signal
            # Пинаем коллектор, чтобы он проверил, есть ли еще действия
            signal = CollectorSignalDTO(session_id=session_id, char_id=0, signal_type="heartbeat", move_id="executor")
            await ctx["redis"].enqueue_job("combat_collector_task", signal.model_dump())

    except Exception:
        # Ловим любые ошибки, чтобы воркер не упал насмерть
        log.exception("ExecutorCriticalError | session_id={session_id}", session_id=session_id)
        raise  # Reraise нужен, чтобы ARQ увидел ошибку и (возможно) сделал retry
