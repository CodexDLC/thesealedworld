from loguru import logger as log

from src.backend.features.combat.dto.worker import AiTurnRequestDTO
from src.backend.features.combat.runtime.services.data_service import CombatDataService  # noqa: TC001
from src.backend.features.combat.services.turn_manager import CombatTurnManager  # noqa: TC001
from src.shared.infrastructure.log_task_wrapper import logged_task


@logged_task
async def ai_turn_task(ctx: dict, request_data: dict) -> None:
    """
    Задача ИИ Агента (AI Agent).

    Принимает решение за NPC (монстров) и регистрирует их действия в системе.
    Выполняется асинхронно, чтобы тяжелые алгоритмы (Minimax/BehaviorTree)
    не блокировали основной цикл боя.

    v2.0: Загрузка полного BattleContext + валидация (is_alive).

    Args:
        ctx: ARQ worker context with AI/runtime dependencies.
        request_data: Serialized AI turn request payload.

    Side Effects:
        Registers one or more runtime intents for the acting NPC through the
        same turn-manager path used by player-authored moves.
    """
    try:
        request = AiTurnRequestDTO(**request_data)

        # Извлечение сервисов
        turn_manager: CombatTurnManager = ctx["turn_manager"]
        ai_processor = ctx["ai_processor"]

        # Получаем сервис данных (с фоллбеком)
        data_service: CombatDataService | None = ctx.get("combat_data_service")
        if not data_service and "combat_collector" in ctx:
            data_service = ctx["combat_collector"].data_service

        if not data_service:
            log.bind(reason="no_data_service", bot_id=request.bot_id).error("AiTurnError")
            return

        # 1. ЗАГРУЗКА ПОЛНОГО КОНТЕКСТА (как в Executor)
        battle_ctx = await data_service.load_battle_context(request.session_id)

        if not battle_ctx or not battle_ctx.meta.active:
            log.bind(reason="inactive_session", session_id=request.session_id).warning("AiTurnSkipped")
            return

        # 2. ИЗВЛЕЧЕНИЕ ДАННЫХ БОТА
        bot = battle_ctx.get_actor(request.bot_id)

        if not bot:
            log.bind(reason="bot_not_found", bot_id=request.bot_id).warning("AiTurnSkipped")
            return

        # 3. ВАЛИДАЦИЯ БОТА (только is_alive, CC игнорируем)
        if not bot.is_alive:
            log.bind(reason="bot_is_dead", bot_id=request.bot_id).warning("AiTurnSkipped")
            return

        # 4. ИЗВЛЕЧЕНИЕ ДАННЫХ ЦЕЛЕЙ
        targets = []
        for target_id in request.missing_targets:
            target = battle_ctx.get_actor(target_id)
            if target and target.is_alive:
                targets.append(target)

        if not targets:
            log.bind(reason="no_valid_targets", bot_id=request.bot_id).warning("AiTurnSkipped")
            return

        log.bind(
            session_id=request.session_id,
            bot_id=request.bot_id,
            valid_targets=[target.meta.id for target in targets],
        ).debug("AiTurnPlan")

        # 5. ПРИНЯТИЕ РЕШЕНИЙ (AI Processor)
        # Prefer turn-level planning: the brain sees all candidate targets at
        # once and allocates finite resources (feint hand, stamina) across the
        # per-target intents. Fallback to per-target decide_exchange only when
        # a custom processor double does not implement decide_turn.
        payloads: list = []
        decide_turn = getattr(ai_processor, "decide_turn", None)
        if callable(decide_turn):
            try:
                payloads = list(decide_turn(bot, battle_ctx, targets))
            except Exception:  # noqa: BLE001 — fall back to legacy path on any inference error
                log.bind(bot_id=request.bot_id, mode="decide_turn").exception("AiDecideTurnFailed")
                payloads = []
        if not payloads:
            for target in targets:
                payloads.append(ai_processor.decide_exchange(bot, target))

        # 6. РЕГИСТРАЦИЯ ХОДОВ
        if payloads:
            await turn_manager.register_moves_batch(request.session_id, request.bot_id, payloads)

        log.bind(session_id=request.session_id, bot_id=request.bot_id, move_count=len(payloads)).info("AiTurnSuccess")

    except Exception:
        log.bind(bot_id=request_data.get("bot_id", "unknown")).exception("AiTurnError")
        raise
