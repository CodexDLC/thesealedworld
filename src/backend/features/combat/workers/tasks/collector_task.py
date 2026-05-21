from loguru import logger as log

from src.backend.features.combat.dto.worker import CollectorSignalDTO, WorkerBatchJobDTO
from src.backend.features.combat.runtime.processors.collector import CombatCollector  # noqa: TC001
from src.backend.features.combat.runtime.services.data_service import CombatDataService  # noqa: TC001
from src.backend.features.combat.workers.tasks.chat_announcements import publish_combat_start_announcement
from src.shared.infrastructure.log_task_wrapper import logged_task


@logged_task
async def combat_collector_task(ctx: dict, signal_data: dict) -> None:
    """
    Задача Коллектора (Matchmaker / Batch Aggregator).

    Отвечает за сбор накопленных действий игроков и формирование пакета (Batch)
    для исполнителя (Executor). Также запускает AI, если пришло время.

    Args:
        ctx: ARQ worker context with collector/data-service dependencies.
        signal_data: Serialized collector signal describing why this cycle ran.

    Side Effects:
        - Enqueues AI jobs for uncovered NPC intents.
        - Enqueues executor jobs when a runnable batch is ready.
        - Enqueues victory finalization when battle end is detected.
    """
    session_id = "unknown"
    try:
        signal = CollectorSignalDTO(**signal_data)
        session_id = signal.session_id

        # Извлечение сервисов
        # ВАЖНО: collector уже инициализирован в combat_arq.py
        collector: CombatCollector = ctx["combat_collector"]
        data_service: CombatDataService = collector.data_service

        log.bind(session_id=session_id, signal=signal.signal_type).debug("CollectorStart")

        # 1. Logic Execution (Collect Actions & Check Timers)
        # Возвращает размер батча, список задач для AI и результат проверки победы
        batch_size, ai_tasks, victory_result = await collector.collect_actions(signal.session_id, signal)
        log.bind(
            session_id=session_id,
            signal=signal.signal_type,
            batch_size=batch_size,
            ai_task_count=len(ai_tasks),
            victory=victory_result,
        ).debug("CollectorResult")
        await publish_combat_start_announcement(ctx, data_service, signal.session_id)

        # 2. Dispatch AI Tasks (Non-blocking)
        if ai_tasks:
            count = 0
            for task in ai_tasks:
                await ctx["redis"].enqueue_job("ai_turn_task", task.model_dump())
                count += 1

            log.bind(session_id=session_id, count=count).info("CollectorDispatchAi")

        # 3. Dispatch Executor Task (Critical Path)
        if batch_size > 0:
            # Atomic Check: Не работает ли уже Executor с этой сессией?
            can_enqueue = await data_service.combat_manager.check_and_lock_busy_for_collector(signal.session_id)

            if can_enqueue:
                job_dto = WorkerBatchJobDTO(session_id=signal.session_id, batch_size=batch_size)
                await ctx["redis"].enqueue_job("execute_batch_task", job_dto.model_dump())

                log.bind(session_id=session_id, batch_size=batch_size).info("CollectorDispatchExec")
            else:
                # Executor занят, оставляем действия в очереди до следующего сигнала
                log.bind(reason="executor_busy", session_id=session_id).debug("CollectorSkip")
        else:
            log.bind(session_id=session_id).debug("CollectorIdle")

        # 4. Victory Finalization (если обнаружена победа)
        if victory_result:
            log.bind(session_id=session_id, winner=victory_result, dispatching_finalizer=True).warning(
                "CollectorVictory"
            )
            # Постановка задачи финализатора в очередь
            finalizer_data = {"session_id": signal.session_id, "winner": victory_result}
            await ctx["redis"].enqueue_job("victory_finalizer_task", finalizer_data)

    except Exception:
        log.bind(session_id=session_id).exception("CollectorError")
        raise
