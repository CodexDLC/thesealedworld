import time
from datetime import UTC, datetime, timedelta

from loguru import logger as log

from src.backend.features.combat.dto.worker import CollectorSignalDTO
from src.backend.features.combat.runtime.processors.chaos_service import ChaosService
from src.backend.features.combat.runtime.services.data_service import CombatDataService  # noqa: TC001
from src.backend.features.monsters.services import AnchorProjectionSnapshotCache
from src.shared.infrastructure.log_task_wrapper import logged_task

# Константа таймаута (10 минут)
MAX_INACTIVITY_SEC = 600


@logged_task
async def chaos_check_task(ctx: dict, session_id: str) -> None:
    """
    Задача Хаоса (Watchdog / Garbage Collector).

    Работает как рекурсивный таймер ("Эстафета"):
    1. Проверяет, жива ли сессия.
    2. Если сессия неактивна > 10 минут, спавнит "Чистильщика" (Force End).
    3. Перезапускает саму себя через 5 минут.

    Args:
        ctx: ARQ worker context with runtime and queue dependencies.
        session_id: Active combat session id to inspect.

    Side Effects:
        - May hot-join the chaos cleaner actor into a stalled combat.
        - May enqueue a collector heartbeat after a chaos spawn.
        - Always re-enqueues itself while the session remains active.
    """
    try:
        # Service Resolution (Lazy Load Pattern)
        # Пытаемся достать сервис, если он есть, иначе фоллбек
        data_service: CombatDataService | None = ctx.get("combat_data_service")

        if not data_service:
            if "combat_collector" in ctx:
                data_service = ctx["combat_collector"].data_service
            else:
                log.bind(reason="service_not_found").error("ChaosError")
                return

        # ChaosService легковесный, создаем on-demand
        redis = ctx.get("redis")
        anchor_snapshots = AnchorProjectionSnapshotCache(redis) if hasattr(redis, "json_module") else None
        chaos_service = ChaosService(data_service, anchor_snapshots=anchor_snapshots)

        # 1. Check Session State
        meta = await data_service.get_battle_meta(session_id)

        if not meta or not meta.active:
            log.bind(reason="session_inactive", session_id=session_id).info("ChaosStop")
            return

        # 2. Check Inactivity (Zombie Session Detection)
        now = int(time.time())
        delta = now - meta.last_activity_at

        if meta.started_at is None:
            log.bind(reason="not_started", session_id=session_id).debug("ChaosSkipped")
        elif delta > MAX_INACTIVITY_SEC:
            # Trigger Cleanup Event
            spawned = await chaos_service.spawn_cleaner(session_id)
            if spawned:
                log.bind(session_id=session_id, inactivity_sec=delta).warning("ChaosCleanerSpawned")
                signal = CollectorSignalDTO(
                    session_id=session_id,
                    char_id="0",
                    signal_type="heartbeat",
                    move_id="chaos_spawn",
                )
                await ctx["redis"].enqueue_job("combat_collector_task", signal.model_dump())
            else:
                log.bind(reason="already_spawned", session_id=session_id).debug("ChaosCleanerSkipped")

        # 3. Relay (Self-Requeue)
        # Планируем следующий чек через 5 минут (300 сек)
        next_check_delay = 300
        await ctx["redis"].enqueue_job(
            "chaos_check_task",
            session_id,
            _defer_until=datetime.now(UTC) + timedelta(seconds=next_check_delay),
        )

        log.bind(session_id=session_id, next_run_in_sec=next_check_delay).debug("ChaosRelay")

    except Exception:  # noqa: BLE001
        log.bind(session_id=session_id).exception("ChaosCriticalError")
        # Не делаем raise, чтобы не забить очередь ретраями упавшей "мусорной" задачи
