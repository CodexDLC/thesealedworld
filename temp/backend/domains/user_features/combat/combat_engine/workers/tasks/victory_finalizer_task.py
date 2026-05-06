from typing import TYPE_CHECKING

from loguru import logger as log

if TYPE_CHECKING:
    from src.backend.domains.user_features.combat.combat_engine.combat_data_service import CombatDataService


async def victory_finalizer_task(ctx: dict, data: dict) -> None:
    """
    Финализатор боя (Victory Finalizer).

    Выполняется после определения победителя.
    Отвечает за завершение боя и начисление наград.

    Args:
        ctx: Контекст ARQ.
        data: Данные финализации (session_id, winner).
    """
    session_id = data.get("session_id", "unknown")
    winner = data.get("winner", "unknown")

    log.info(
        "VictoryFinalizer | session_id={session_id} winner={winner} status=processing",
        session_id=session_id,
        winner=winner,
    )

    data_service: CombatDataService | None = ctx.get("combat_data_service")
    if not data_service:
        log.error("VictoryFinalizer | CombatDataService not found in context")
        return

    try:
        # 1. Устанавливаем статус победы в Redis
        await data_service.set_battle_winner(session_id, winner)

        # 2. (Future) Начисление наград, XP, сохранение в БД
        # TODO: Реализовать начисление наград

        log.info(f"VictoryFinalizer | Battle {session_id} finalized successfully")

    except Exception as e:  # noqa: BLE001
        log.exception(f"VictoryFinalizer | Failed to finalize battle {session_id}: {e}")
