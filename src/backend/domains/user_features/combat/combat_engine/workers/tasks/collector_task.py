from loguru import logger as log

from src.backend.domains.user_features.combat.combat_engine.combat_data_service import CombatDataService
from src.backend.domains.user_features.combat.combat_engine.processors.collector import CombatCollector
from src.backend.domains.user_features.combat.dto.combat_arq_dto import CollectorSignalDTO, WorkerBatchJobDTO


async def combat_collector_task(ctx: dict, signal_data: dict) -> None:
    """
    Задача Коллектора (Matchmaker / Batch Aggregator).

    Отвечает за сбор накопленных действий игроков и формирование пакета (Batch)
    для исполнителя (Executor). Также запускает AI, если пришло время.

    Args:
        ctx: Контекст ARQ с инъекциями сервисов.
        signal_data: Данные сигнала (CollectorSignalDTO).
    """
    session_id = "unknown"
    try:
        signal = CollectorSignalDTO(**signal_data)
        session_id = signal.session_id

        # Извлечение сервисов
        # ВАЖНО: collector уже инициализирован в combat_arq.py
        collector: CombatCollector = ctx["combat_collector"]
        data_service: CombatDataService = collector.data_service

        log.debug(
            "CollectorStart | session_id={session_id} signal={signal}", session_id=session_id, signal=signal.signal_type
        )

        # 1. Logic Execution (Collect Actions & Check Timers)
        # Возвращает размер батча, список задач для AI и результат проверки победы
        batch_size, ai_tasks, victory_result = await collector.collect_actions(signal.session_id, signal)

        # 2. Dispatch AI Tasks (Non-blocking)
        if ai_tasks:
            count = 0
            for task in ai_tasks:
                await ctx["redis"].enqueue_job("ai_turn_task", task.model_dump())
                count += 1

            log.info("CollectorDispatchAI | session_id={session_id} count={count}", session_id=session_id, count=count)

        # 3. Dispatch Executor Task (Critical Path)
        if batch_size > 0:
            # Atomic Check: Не работает ли уже Executor с этой сессией?
            can_enqueue = await data_service.combat_manager.check_and_lock_busy_for_collector(signal.session_id)

            if can_enqueue:
                job_dto = WorkerBatchJobDTO(session_id=signal.session_id, batch_size=batch_size)
                await ctx["redis"].enqueue_job("execute_batch_task", job_dto.model_dump())

                log.info(
                    "CollectorDispatchExec | session_id={session_id} batch={batch}",
                    session_id=session_id,
                    batch=batch_size,
                )
            else:
                # Executor занят, оставляем действия в очереди до следующего сигнала
                log.info("CollectorSkip | reason=executor_busy session_id={session_id}", session_id=session_id)
        else:
            log.debug("CollectorIdle | session_id={session_id}", session_id=session_id)

        # 4. Victory Finalization (если обнаружена победа)
        if victory_result:
            log.warning(
                "CollectorVictory | session_id={session_id} winner={winner} dispatching_finalizer=True",
                session_id=session_id,
                winner=victory_result,
            )
            # Постановка задачи финализатора в очередь
            finalizer_data = {"session_id": signal.session_id, "winner": victory_result}
            await ctx["redis"].enqueue_job("victory_finalizer_task", finalizer_data)

    except Exception:
        log.exception("CollectorError | session_id={session_id}", session_id=session_id)
        raise
