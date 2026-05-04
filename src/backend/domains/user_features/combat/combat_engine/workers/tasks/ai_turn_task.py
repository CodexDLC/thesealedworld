from loguru import logger as log

from src.backend.domains.user_features.combat.combat_engine.combat_data_service import CombatDataService
from src.backend.domains.user_features.combat.dto.combat_arq_dto import AiTurnRequestDTO
from src.backend.domains.user_features.combat.orchestrators.handler.runtime.combat_turn_manager import CombatTurnManager


async def ai_turn_task(ctx: dict, request_data: dict) -> None:
    """
    Задача ИИ Агента (AI Agent).

    Принимает решение за NPC (монстров) и регистрирует их действия в системе.
    Выполняется асинхронно, чтобы тяжелые алгоритмы (Minimax/BehaviorTree)
    не блокировали основной цикл боя.

    v2.0: Загрузка полного BattleContext + валидация (is_alive).

    Args:
        ctx: Контекст ARQ.
        request_data: Данные запроса (AiTurnRequestDTO).
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
            log.error("AiTurnError | reason=no_data_service bot_id={bot_id}", bot_id=request.bot_id)
            return

        # 1. ЗАГРУЗКА ПОЛНОГО КОНТЕКСТА (как в Executor)
        battle_ctx = await data_service.load_battle_context(request.session_id)

        if not battle_ctx or not battle_ctx.meta.active:
            log.warning("AiTurnSkip | reason=inactive_session session_id={session_id}", session_id=request.session_id)
            return

        # 2. ИЗВЛЕЧЕНИЕ ДАННЫХ БОТА
        bot = battle_ctx.get_actor(request.bot_id)

        if not bot:
            log.warning("AiTurnSkip | reason=bot_not_found bot_id={bot_id}", bot_id=request.bot_id)
            return

        # 3. ВАЛИДАЦИЯ БОТА (только is_alive, CC игнорируем)
        if not bot.is_alive:
            log.warning("AiTurnSkip | reason=bot_is_dead bot_id={bot_id}", bot_id=request.bot_id)
            return

        # 4. ИЗВЛЕЧЕНИЕ ДАННЫХ ЦЕЛЕЙ
        targets = []
        for target_id in request.missing_targets:
            target = battle_ctx.get_actor(target_id)
            if target and target.is_alive:
                targets.append(target)

        if not targets:
            log.warning("AiTurnSkip | reason=no_valid_targets bot_id={bot_id}", bot_id=request.bot_id)
            return

        # 5. ПРИНЯТИЕ РЕШЕНИЙ (AI Processor)
        payloads = []
        for target in targets:
            payload = ai_processor.decide_exchange(bot, target)
            payloads.append(payload)

        # 6. РЕГИСТРАЦИЯ ХОДОВ
        if payloads:
            await turn_manager.register_moves_batch(request.session_id, request.bot_id, payloads)

        log.info(
            "AiTurnSuccess | session_id={session_id} bot_id={bot_id} moves={count}",
            session_id=request.session_id,
            bot_id=request.bot_id,
            count=len(payloads),
        )

    except Exception:
        log.exception("AiTurnError | bot_id={bot_id}", bot_id=request_data.get("bot_id", "unknown"))
        raise
