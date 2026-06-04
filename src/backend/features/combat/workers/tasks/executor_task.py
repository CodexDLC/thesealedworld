import contextlib
import time

from loguru import logger as log

from src.backend.features.combat.dto.action import CombatActionDTO
from src.backend.features.combat.dto.worker import CollectorSignalDTO, WorkerBatchJobDTO
from src.backend.features.combat.runtime.engine.tunables import load_combat_tunables, use_tunables
from src.backend.features.combat.runtime.processors.executor import CombatExecutor  # noqa: TC001
from src.backend.features.combat.runtime.services.data_service import CombatDataService  # noqa: TC001
from src.backend.realtime.integrations.notice_publisher import (
    PlayerNoticePublisher,
    RawStreamNoticeProducer,
    RefreshTargets,
)
from src.shared.infrastructure.log_task_wrapper import logged_task


@logged_task
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
        ctx: ARQ worker context with executor and data-service dependencies.
        job_data: Serialized executor batch job contract.

    Side Effects:
        - Loads full battle context from runtime storage.
        - Acquires and releases the distributed executor lock.
        - Commits battle state, logs, dead actors, and target returns.
        - Enqueues support jobs and a collector heartbeat.
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
                log.bind(reason="service_not_found").error("ExecutorFailed")
                return

        # 1. Load Context (Heavy IO)
        battle_ctx = await data_service.load_battle_context(session_id)

        if not battle_ctx or not battle_ctx.meta.active:
            log.bind(reason="inactive_session", session_id=session_id).warning("ExecutorSkipped")
            # Снимаем зависшие блокировки, если есть
            if data_service:
                await data_service.combat_manager.release_worker_lock_safe(session_id, "force")
            return

        # 2. Acquire Worker Lock (Concurrency Check)
        # Гарантирует, что только один executor пишет в базу для этой сессии
        acquired = await data_service.combat_manager.acquire_worker_lock(session_id, my_id)
        if not acquired:
            log.bind(reason="locked_by_other", session_id=session_id).warning("ExecutorSkipped")
            return

        try:
            # 3. Fetch Actions from Redis Queue
            # Берем пачку действий
            raw_actions = await data_service.load_actions_batch(session_id, job.batch_size)

            if not raw_actions:
                log.bind(session_id=session_id).debug("ExecutorEmpty")
                return

            actions = []
            invalid_actions = 0
            for raw in raw_actions:
                try:
                    # Валидируем JSON, битые пакеты игнорируем
                    actions.append(CombatActionDTO.model_validate_json(raw))
                except Exception:
                    invalid_actions += 1

            log.bind(
                session_id=session_id,
                requested_count=job.batch_size,
                raw_count=len(raw_actions),
                parsed_count=len(actions),
                invalid_count=invalid_actions,
                step=battle_ctx.meta.step_counter,
            ).debug("ExecutorBatchLoaded")

            # 4. Process Batch (Pure Logic Calculation)
            # Вся математика происходит тут. Снимок tunables на батч —
            # одно чтение Redis, далее resolver достаёт значения через ContextVar.
            tunables = await load_combat_tunables(ctx.get("game_config"))
            with use_tunables(tunables):
                processed_ids = await executor.process_batch(battle_ctx, actions)
            log.bind(
                session_id=session_id,
                processed_count=len(processed_ids),
                step=battle_ctx.meta.step_counter,
                log_count=len(battle_ctx.pending_logs),
                death_count=len(battle_ctx.pending_dead_actors),
                target_return_count=len(battle_ctx.pending_target_returns),
            ).debug("ExecutorBatchProcessed")

            # 5. Commit (Zombie Check & Save)
            # Перед записью проверяем, не истек ли наш лок пока мы считали
            is_mine = await data_service.combat_manager.check_worker_lock(session_id, my_id)

            if not is_mine:
                log.bind(session_id=session_id, error="lock_lost_during_calc").error("ExecutorZombieDetected")
                return

            # 5.1. АТОМАРНЫЙ Save (state + logs + actions + targets)
            await data_service.commit_session(battle_ctx, processed_ids)
            await _enqueue_result_support_tasks(ctx, battle_ctx)
            await _publish_combat_refresh_notices(ctx, battle_ctx)

            log.bind(
                session_id=session_id,
                processed_count=len(processed_ids),
                step=battle_ctx.meta.step_counter,
                log_count=len(battle_ctx.pending_logs),
                death_count=len(battle_ctx.pending_dead_actors),
                target_return_count=len(battle_ctx.pending_target_returns),
            ).info("ExecutorCompleted")

        finally:
            # 6. Release Lock
            await data_service.combat_manager.release_worker_lock_safe(session_id, my_id)

            # 7. Heartbeat Signal
            # Пинаем коллектор, чтобы он проверил, есть ли еще действия
            signal = CollectorSignalDTO(session_id=session_id, char_id="0", signal_type="heartbeat", move_id="executor")
            await ctx["redis"].enqueue_job("combat_collector_task", signal.model_dump())

    except Exception:
        # Ловим любые ошибки, чтобы воркер не упал насмерть
        log.bind(session_id=session_id).exception("ExecutorCriticalError")
        raise  # Reraise нужен, чтобы ARQ увидел ошибку и (возможно) сделал retry


async def _enqueue_result_support_tasks(ctx: dict, battle_ctx) -> None:
    """Enqueue post-resolution support tasks produced during executor processing."""
    payloads = getattr(battle_ctx, "pending_result_support_tasks", None) or []
    if not payloads:
        return

    queue = ctx.get("redis")
    if queue is None:
        log.bind(reason="no_arq", session_id=battle_ctx.session_id).warning("CombatResultSupportSkipped")
        return

    enqueued = 0
    for payload in payloads:
        try:
            await queue.enqueue_job("combat_result_support_task", payload)
            enqueued += 1
        except Exception:
            log.bind(session_id=battle_ctx.session_id, seq=payload.get("seq")).exception(
                "CombatResultSupportEnqueueFailed"
            )
            continue

    log.bind(session_id=battle_ctx.session_id, task_count=enqueued).info("CombatResultSupportEnqueued")


def _player_recipients(battle_ctx) -> list[str]:
    recipients: list[str] = []
    for actor_id, actor in battle_ctx.actors.items():
        actor_type = getattr(actor.meta, "type", None)
        if actor_type == "monster":
            continue
        value = str(actor_id)
        if value.startswith("-"):
            continue
        recipients.append(value)
    return recipients


async def _publish_combat_refresh_notices(ctx: dict, battle_ctx) -> None:
    """Send realtime refresh notifications to all active player participants."""
    redis = ctx.get("redis_client_internal")
    if redis is None:
        return

    recipients = _player_recipients(battle_ctx)
    if not recipients:
        return

    notice_publisher = PlayerNoticePublisher(RawStreamNoticeProducer(redis))
    for actor_id in recipients:
        with contextlib.suppress(Exception):
            await notice_publisher.request_refresh(
                int(actor_id),
                target=RefreshTargets.STATUS,
                reason="combat_turn_resolved",
                domain="combat",
            )
