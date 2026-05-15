import time
from datetime import UTC, datetime, timedelta

from loguru import logger as log

from src.backend.features.combat.dto.worker import CollectorSignalDTO
from src.backend.features.combat.runtime.processors.chaos_service import ChaosService
from src.backend.features.combat.runtime.services.data_service import CombatDataService  # noqa: TC001
from src.backend.features.monsters.services import AnchorProjectionSnapshotCache

# Константа таймаута (10 минут)
MAX_INACTIVITY_SEC = 600


async def chaos_check_task(ctx: dict, session_id: str) -> None:
    """
    Задача Хаоса (Watchdog / Garbage Collector).

    Работает как рекурсивный таймер ("Эстафета"):
    1. Проверяет, жива ли сессия.
    2. Если сессия неактивна > 10 минут, спавнит "Чистильщика" (Force End).
    3. Перезапускает саму себя через 5 минут.

    Args:
        ctx: Контекст ARQ.
        session_id: ID боевой сессии.
    """
    try:
        # Service Resolution (Lazy Load Pattern)
        # Пытаемся достать сервис, если он есть, иначе фоллбек
        data_service: CombatDataService | None = ctx.get("combat_data_service")

        if not data_service:
            if "combat_collector" in ctx:
                data_service = ctx["combat_collector"].data_service
            else:
                log.error("ChaosError | reason=service_not_found")
                return

        # ChaosService легковесный, создаем on-demand
        redis = ctx.get("redis")
        anchor_snapshots = AnchorProjectionSnapshotCache(redis) if hasattr(redis, "json_module") else None
        chaos_service = ChaosService(data_service, anchor_snapshots=anchor_snapshots)

        # 1. Check Session State
        meta = await data_service.get_battle_meta(session_id)

        if not meta or not meta.active:
            log.info("ChaosStop | reason=session_inactive session_id={session_id}", session_id=session_id)
            return

        # 2. Check Inactivity (Zombie Session Detection)
        now = int(time.time())
        delta = now - meta.last_activity_at

        if delta > MAX_INACTIVITY_SEC:
            # Trigger Cleanup Event
            spawned = await chaos_service.spawn_cleaner(session_id)
            if spawned:
                log.warning(
                    "ChaosCleanerSpawned | session_id={session_id} inactivity_sec={delta}",
                    session_id=session_id,
                    delta=delta,
                )
                signal = CollectorSignalDTO(
                    session_id=session_id,
                    char_id="0",
                    signal_type="heartbeat",
                    move_id="chaos_spawn",
                )
                await ctx["redis"].enqueue_job("combat_collector_task", signal.model_dump())
            else:
                log.debug("ChaosCleanerSkip | reason=already_spawned session_id={session_id}", session_id=session_id)

        # 3. Relay (Self-Requeue)
        # Планируем следующий чек через 5 минут (300 сек)
        next_check_delay = 300
        await ctx["redis"].enqueue_job(
            "chaos_check_task",
            session_id,
            _defer_until=datetime.now(UTC) + timedelta(seconds=next_check_delay),
        )

        log.debug(
            "ChaosRelay | session_id={session_id} next_run_in={delay}s", session_id=session_id, delay=next_check_delay
        )

    except Exception:  # noqa: BLE001
        log.exception("ChaosCriticalError | session_id={session_id}", session_id=session_id)
        # Не делаем raise, чтобы не забить очередь ретраями упавшей "мусорной" задачи
