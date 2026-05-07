import asyncio
import time

from loguru import logger as log

from src.backend.features.combat.dto.action import CombatActionDTO
from src.backend.features.combat.dto.pipeline import InteractionResultDTO
from src.backend.features.combat.dto.session import BattleContext
from src.backend.features.combat.runtime.engine.pipeline import CombatPipeline


class CombatExecutor:
    """
    Исполнитель (Executor Processor).
    Чистая бизнес-логика обработки батча действий.
    Управляет потоком выполнения (Flow Control), делегируя расчеты в Pipeline.
    """

    def __init__(self):
        self.pipeline = CombatPipeline()

    async def process_batch(self, ctx: BattleContext, actions: list[CombatActionDTO]) -> list[str]:
        """
        Обрабатывает список действий, изменяя BattleContext in-place.
        Возвращает список ID успешно обработанных действий.
        """
        processed_ids = []

        for action in actions:
            try:
                await self._process_single_action(ctx, action)
                processed_ids.append(action.move.move_id)
            except Exception as e:  # noqa: BLE001
                log.error(f"Executor | Action {action.move.move_id} failed: {e}")
                processed_ids.append(action.move.move_id)

        # Сбор мертвых акторов после обработки батча
        self._collect_dead_actors(ctx)

        return processed_ids

    async def _process_single_action(self, ctx: BattleContext, action: CombatActionDTO) -> None:
        """
        Обработка одного действия.
        Точка входа и маршрутизации (Routing).
        """
        if not action.move:
            log.warning("Executor | Action has no move data")
            return

        # Routing Logic
        # payload is object, use getattr
        target_id = getattr(action.move.payload, "target_id", None)

        if action.action_type == "exchange" or (action.is_forced and target_id):
            await self._handle_exchange(ctx, action)
        else:
            # Instant / Item (Одностороннее воздействие)
            await self._handle_unidirectional(ctx, action)

    # ==========================================================================
    # 🌿 BRANCHES (Logic Flow)
    # ==========================================================================

    async def _handle_exchange(self, ctx: BattleContext, action: CombatActionDTO) -> None:
        """
        Ветка: Обмен ударами (Exchange).
        Обрабатывает цепочку атак (Waves) внутри одного контекста.
        Использует Chain Reactions из DTO результата.
        """
        source = ctx.get_actor(action.move.char_id)
        target_id = getattr(action.move.payload, "target_id", None)
        target = ctx.get_actor(int(target_id)) if target_id else None

        if not source or not target:
            log.warning(f"Executor | Exchange participants not found: {action.move.char_id} -> {target_id}")
            return

        # Очередь задач (Waves)
        pending_tasks = []

        # 1. Main Attack (A -> B)
        pending_tasks.append(self._create_task(source, target, action.move, mods={"action_mode": "exchange"}))  # type: ignore # TODO: Fix later when refactoring Combat Engine

        # 2. Partner Attack (B -> A)
        if action.partner_move:
            pending_tasks.append(
                self._create_task(target, source, action.partner_move, mods={"action_mode": "exchange"})  # type: ignore # TODO: Fix later when refactoring Combat Engine
            )
        elif not action.is_forced:
            log.error("Executor | Exchange without partner_move and not forced")
            return

        # --- EXECUTION LOOP (Waves) ---
        max_waves = 3
        wave = 0

        while pending_tasks and wave < max_waves:
            wave += 1

            # Запускаем текущую волну
            results = await asyncio.gather(*pending_tasks)
            pending_tasks = []

            for result in results:
                s_id = result.source_id
                t_id = result.target_id

                log.debug(
                    "Executor | Result [{}->{}] ({}): outcome={} hit={} crit={} dmg={} heal={} events={}",
                    s_id,
                    t_id,
                    result.hand,
                    self._result_outcome(result),
                    result.is_hit,
                    result.is_crit,
                    result.damage_final,
                    result.healing_final,
                    [event.type for event in result.events],
                )
                self._append_result_logs(ctx, result, action=action, wave=wave)

                # --- CHAIN REACTIONS ---

                # 1. Counter-Attack
                if result.chain_events.trigger_counter_attack:
                    defender = ctx.get_actor(t_id)
                    attacker = ctx.get_actor(s_id)

                    if defender and attacker:
                        log.info(f"Executor | Chain: Counter-Attack {t_id} -> {s_id}")
                        counter_move = action.partner_move if action.partner_move else action.move
                        pending_tasks.append(
                            self._create_task(
                                defender,
                                attacker,
                                counter_move,
                                mods={"is_counter_attack": True, "action_mode": "exchange"},  # type: ignore # TODO: Fix later when refactoring Combat Engine
                            )
                        )

                # 2. Off-Hand Attack
                if result.chain_events.trigger_offhand_attack:
                    attacker = ctx.get_actor(s_id)
                    defender = ctx.get_actor(t_id)

                    if attacker and defender:
                        log.info(f"Executor | Chain: Off-Hand Attack {s_id} -> {t_id}")
                        pending_tasks.append(
                            self._create_task(
                                attacker,
                                defender,
                                action.move,
                                mods={"hand": "off", "action_mode": "exchange"},  # type: ignore # TODO: Fix later when refactoring Combat Engine
                            )
                        )

        # --- FINALIZE ---
        source.meta.exchange_counter += 1
        target.meta.exchange_counter += 1
        ctx.meta.step_counter += 1

        # НОВОЕ: Собираем пары для возврата целей
        self._collect_target_returns(ctx, action)

        log.info(f"Executor | Exchange complete. Waves={wave}. Global step={ctx.meta.step_counter}")

    async def _handle_unidirectional(self, ctx: BattleContext, action: CombatActionDTO) -> None:
        """
        Ветка: Одностороннее действие.
        """
        source = ctx.get_actor(action.move.char_id)
        if not source:
            return

        target_ids = action.move.targets or []

        # Check for self target in payload
        payload_target = getattr(action.move.payload, "target_id", None)
        if action.move.strategy == "item" and payload_target == "self":
            target_ids = [int(source.char_id)]

        tasks = []
        for tid in target_ids:
            target = ctx.get_actor(tid)
            if target:
                tasks.append(self._create_task(source, target, action.move, mods={"action_mode": "unidirectional"}))  # type: ignore # TODO: Fix later when refactoring Combat Engine

        if tasks:
            results = await asyncio.gather(*tasks)
            for result in results:
                self._append_result_logs(ctx, result, action=action, wave=1)
            log.info(f"Executor | Unidirectional complete. Targets={len(tasks)}")

    # ==========================================================================
    # 🛠️ HELPERS
    # ==========================================================================

    def _create_task(self, source, target, move, mods=None):
        """
        Создает задачу для Pipeline.
        Инкапсулирует передачу exchange_count и других параметров.
        """
        return self.pipeline.calculate(
            source=source,
            target=target,
            move=move,
            external_mods=mods,
            exchange_count=source.meta.exchange_counter,
        )

    def _append_result_logs(
        self, ctx: BattleContext, result: InteractionResultDTO, *, action: CombatActionDTO, wave: int
    ) -> None:
        """
        Переносит уже рассчитанные pipeline events в боевой log buffer.

        Это технический runtime-log для текущего браузерного интерфейса. Текстовые описания,
        локализация и компактное архивное хранение должны появиться отдельным log service.
        TODO(combat-logs): заменить этот временный перенос на CombatLogBuilder, который получает
        полный InteractionResultDTO, action, source/target snapshots, wave/action_mode и catalog
        text layer, а затем собирает structured exchange summary и человекочитаемые тексты.
        """
        timestamp = time.time()
        common_tags = ["runtime", action.action_type, f"wave:{wave}"]
        if action.is_forced:
            common_tags.append("forced")

        if result.events:
            for event in result.events:
                entry = event.model_dump(mode="json")
                entry["timestamp"] = timestamp
                entry["tags"] = [*entry.get("tags", []), *common_tags]
                entry["text"] = self._build_technical_log_text(entry)
                ctx.pending_logs.append(entry)
            return

        ctx.pending_logs.append(
            {
                "type": "RESULT",
                "text": self._build_technical_log_text(
                    {
                        "type": "RESULT",
                        "source_id": result.source_id,
                        "target_id": result.target_id,
                        "value": result.damage_final or result.healing_final or None,
                    }
                ),
                "timestamp": timestamp,
                "tags": common_tags,
                "source_id": result.source_id,
                "target_id": result.target_id,
                "damage_final": result.damage_final,
                "healing_final": result.healing_final,
                "skip_reason": result.skip_reason,
            }
        )

    @staticmethod
    def _build_technical_log_text(entry: dict) -> str:
        event_type = entry.get("type") or "RESULT"
        source_id = entry.get("source_id")
        target_id = entry.get("target_id")
        value = entry.get("value")
        resource = entry.get("resource")

        text = f"{event_type}: {source_id}"
        if target_id is not None:
            text += f" -> {target_id}"
        if value is not None:
            text += f" {value}"
            if resource:
                text += f" {resource}"
        return text

    def _collect_target_returns(self, ctx: BattleContext, action: CombatActionDTO) -> None:
        """
        Собирает пары (source_id, target_id) для возврата в очереди после Exchange.

        Логика:
        - Source всегда возвращает target в свою очередь
        - Target возвращает source в свою очередь (если был partner_move)
        - Если не было partner_move (forced attack) - target не возвращает
        """
        source_id = str(action.move.char_id)
        target_id_raw = getattr(action.move.payload, "target_id", None)

        if not target_id_raw:
            return

        target_id = int(target_id_raw)

        # Source -> Target (всегда)
        ctx.pending_target_returns.append({"source_id": source_id, "target_id": target_id})  # type: ignore # TODO: Fix later when refactoring Combat Engine

        # Target -> Source (только если был ответ)
        if action.partner_move:
            ctx.pending_target_returns.append({"source_id": str(target_id), "target_id": int(source_id)})  # type: ignore # TODO: Fix later when refactoring Combat Engine

    def _collect_dead_actors(self, ctx: BattleContext) -> None:
        """
        Собирает ID умерших акторов для обновления meta.dead_actors.
        Проверяет всех акторов в контексте и добавляет мертвых в pending_dead_actors.
        """
        for char_id, actor in ctx.actors.items():
            # Проверяем, что актор мертв и еще не в списке мертвых
            if actor.meta.is_dead and char_id not in ctx.meta.dead_actors and char_id not in ctx.pending_dead_actors:
                ctx.pending_dead_actors.append(char_id)

    @staticmethod
    def _result_outcome(result: InteractionResultDTO) -> str:
        if result.skip_reason:
            return result.skip_reason.lower()
        if result.is_miss:
            return "miss"
        if result.is_dodged:
            return "dodge"
        if result.is_parried:
            return "parry"
        if result.is_blocked:
            return "block"
        if result.is_hit:
            return "crit" if result.is_crit else "hit"
        if result.healing_final > 0:
            return "heal"
        return "none"
