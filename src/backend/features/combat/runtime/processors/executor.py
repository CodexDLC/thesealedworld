import asyncio
import time
from collections.abc import Awaitable
from typing import Any, cast

from loguru import logger as log

from src.backend.features.combat.dto.action import CombatActionDTO, CombatMoveDTO
from src.backend.features.combat.dto.actor import ActorSnapshot
from src.backend.features.combat.dto.ids import ActorId, ActorIdLike, normalize_actor_id
from src.backend.features.combat.dto.pipeline import InteractionResultDTO, PipelineContextDTO
from src.backend.features.combat.dto.session import BattleContext, TargetReturnDTO
from src.backend.features.combat.integrations import CombatCatalogIntegrator
from src.backend.features.combat.runtime.engine.feint_service import FeintService
from src.backend.features.combat.runtime.engine.pipeline import CombatPipeline
from src.backend.features.combat.runtime.engine.target_resolver import TargetResolver
from src.backend.features.combat.runtime.support import (
    CombatAnalyticsFactBuilder,
    CombatLogBuilder,
    CombatResultSupportTaskDTO,
)
from src.backend.features.game_catalog.combat.resources.common.targeting import TargetType


class CombatExecutor:
    """
    Исполнитель (Executor Processor).
    Чистая бизнес-логика обработки батча действий.
    Управляет потоком выполнения (Flow Control), делегируя расчеты в Pipeline.
    """

    def __init__(self):
        self.pipeline = CombatPipeline()
        self.target_resolver = TargetResolver()

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
        target = ctx.get_actor(cast("ActorIdLike", target_id)) if target_id else None

        if not source or not target:
            log.warning(f"Executor | Exchange participants not found: {action.move.char_id} -> {target_id}")
            return

        self._process_periodic_effects(ctx, [source, target], action=action, wave=0)

        # Очередь задач (Waves)
        pending_tasks: list[tuple[Awaitable[InteractionResultDTO], CombatMoveDTO]] = []

        # 1. Main Attack (A -> B)
        pending_tasks.append(
            (self._create_task(source, target, action.move, mods={"action_mode": "exchange"}), action.move)
        )

        # 2. Partner Attack (B -> A)
        if action.partner_move:
            pending_tasks.append(
                (
                    self._create_task(target, source, action.partner_move, mods={"action_mode": "exchange"}),
                    action.partner_move,
                )
            )
        elif not action.is_forced:
            log.error("Executor | Exchange without partner_move and not forced")
            return

        for secondary_target in self._secondary_feint_targets(
            ctx, action, primary_target_id=normalize_actor_id(cast("ActorIdLike", target_id))
        ):
            pending_tasks.append(
                (
                    self._create_task(
                        source,
                        secondary_target,
                        action.move,
                        mods={"action_mode": "exchange", "damage_mult": 0.5, "feint_role": "secondary"},
                    ),
                    action.move,
                )
            )

        # --- EXECUTION LOOP (Waves) ---
        max_waves = 3
        wave = 0

        while pending_tasks and wave < max_waves:
            wave += 1

            # Запускаем текущую волну
            current_tasks = pending_tasks
            results = await asyncio.gather(*(task for task, _move in current_tasks))
            pending_tasks = []

            for result, move in zip(results, (move for _task, move in current_tasks), strict=False):
                result_action = self._action_for_move(action, move, result=result)
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
                self._append_result_logs(ctx, result, action=result_action, wave=wave)
                self._append_result_support_payload(ctx, result, action=result_action, wave=wave)
                self._log_result_info(ctx, result, wave=wave)
                self._refund_feint_cost_if_needed(ctx, result, move)
                if s_id is None or t_id is None:
                    log.warning("Executor | Result has no actor ids; skipping chain reactions")
                    continue

                # --- CHAIN REACTIONS ---

                # 1. Counter-Attack
                if result.chain_events.trigger_counter_attack:
                    defender = ctx.get_actor(t_id)
                    attacker = ctx.get_actor(s_id)

                    if defender and attacker:
                        log.info(f"Executor | Chain: Counter-Attack {t_id} -> {s_id}")
                        counter_move = action.partner_move if action.partner_move else action.move
                        pending_tasks.append(
                            (
                                self._create_task(
                                    defender,
                                    attacker,
                                    counter_move,
                                    mods={"is_counter_attack": True, "action_mode": "exchange"},
                                ),
                                counter_move,
                            )
                        )

                # 2. Off-Hand Attack
                if result.chain_events.trigger_offhand_attack:
                    attacker = ctx.get_actor(s_id)
                    defender = ctx.get_actor(t_id)

                    if attacker and defender:
                        log.info(f"Executor | Chain: Off-Hand Attack {s_id} -> {t_id}")
                        pending_tasks.append(
                            (
                                self._create_task(
                                    attacker,
                                    defender,
                                    action.move,
                                    mods={"hand": "off", "action_mode": "exchange"},
                                ),
                                action.move,
                            )
                        )

        # --- FINALIZE ---
        source.meta.exchange_counter += 1
        target.meta.exchange_counter += 1
        ctx.meta.step_counter += 1

        self._reroll_exchange_feints(source)
        self._reroll_exchange_feints(target)

        # НОВОЕ: Собираем пары для возврата целей
        self._collect_target_returns(ctx, action)

        log.info(f"Executor | Exchange complete. Waves={wave}. Global step={ctx.meta.step_counter}")

    @staticmethod
    def _action_for_move(
        action: CombatActionDTO,
        move: CombatMoveDTO,
        *,
        result: InteractionResultDTO | None = None,
    ) -> CombatActionDTO:
        result_targets = [result.target_id] if result and result.target_id is not None else move.targets
        move_for_log = move.model_copy(update={"targets": result_targets})
        return CombatActionDTO(
            action_type=action.action_type,
            move=move_for_log,
            partner_move=None,
            is_forced=action.is_forced,
        )

    async def _handle_unidirectional(self, ctx: BattleContext, action: CombatActionDTO) -> None:
        """
        Ветка: Одностороннее действие.
        """
        source = ctx.get_actor(action.move.char_id)
        if not source:
            return

        self._process_periodic_effects(ctx, [source], action=action, wave=0)

        target_ids = action.move.targets or []

        # Check for self target in payload
        payload_target = getattr(action.move.payload, "target_id", None)
        if action.move.strategy == "item" and payload_target == "self":
            target_ids = [source.char_id]

        tasks: list[Awaitable[InteractionResultDTO]] = []
        for tid in target_ids:
            target = ctx.get_actor(tid)
            if target:
                tasks.append(self._create_task(source, target, action.move, mods={"action_mode": "unidirectional"}))

        if tasks:
            results = await asyncio.gather(*tasks)
            for result in results:
                self._append_result_logs(ctx, result, action=action, wave=1)
                self._append_result_support_payload(ctx, result, action=action, wave=1)
                self._log_result_info(ctx, result, wave=1)
            log.info(f"Executor | Unidirectional complete. Targets={len(tasks)}")

    # ==========================================================================
    # 🛠️ HELPERS
    # ==========================================================================

    def _create_task(
        self,
        source: ActorSnapshot,
        target: ActorSnapshot | None,
        move: CombatMoveDTO,
        mods: dict[str, Any] | None = None,
    ) -> Awaitable[InteractionResultDTO]:
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

    def _secondary_feint_targets(
        self, ctx: BattleContext, action: CombatActionDTO, *, primary_target_id: ActorId
    ) -> list[ActorSnapshot]:
        feint_id = getattr(action.move.payload, "feint_id", None)
        if not feint_id:
            return []

        feint_entry = CombatCatalogIntegrator.get_feint_catalog_entry(str(feint_id))
        if not feint_entry:
            return []
        feint_config = feint_entry.technical
        if feint_config.target != TargetType.ALL_ENEMIES or feint_config.target_count <= 1:
            return []

        resolved = self.target_resolver.resolve(action.move.char_id, feint_config.target.value, ctx.meta)
        limit = max(0, int(feint_config.target_count) - 1)
        selected: list[ActorSnapshot] = []
        for target_id in resolved:
            if target_id in {action.move.char_id, primary_target_id}:
                continue
            actor = ctx.get_actor(target_id)
            if actor and actor.is_alive:
                selected.append(actor)
            if len(selected) >= limit:
                break
        return selected

    def _process_periodic_effects(
        self, ctx: BattleContext, actors: list[Any], *, action: CombatActionDTO, wave: int
    ) -> None:
        seen: set[ActorId] = set()
        for actor in actors:
            actor_id = actor.char_id
            if actor_id in seen:
                continue
            seen.add(actor_id)

            tick_ctx = PipelineContextDTO()
            tick_ctx.flags.mechanics.apply_periodic = True
            self.pipeline.mechanics_service.process_turn_start(tick_ctx, actor)
            if tick_ctx.result.events:
                self._append_result_logs(ctx, tick_ctx.result, action=action, wave=wave)
                self._append_result_support_payload(ctx, tick_ctx.result, action=action, wave=wave)
                self._log_result_info(ctx, tick_ctx.result, wave=wave)

    @staticmethod
    def _refund_feint_cost_if_needed(ctx: BattleContext, result: InteractionResultDTO, move: CombatMoveDTO) -> None:
        if not result.chain_events.preserve_feint:
            return

        feint_id = getattr(move.payload, "feint_id", None)
        if not feint_id:
            return

        source = ctx.get_actor(move.char_id)
        if not source:
            return

        feint_entry = CombatCatalogIntegrator.get_feint_catalog_entry(feint_id)
        if not feint_entry:
            log.warning("Executor | Feint refund failed: unknown feint_id={}", feint_id)
            return

        feint_config = feint_entry.technical
        FeintService.refund_cost(source.meta, dict(feint_config.cost.tactics))

    @staticmethod
    def _reroll_exchange_feints(actor) -> None:
        hand_size = actor.stats.mods.hand_size if actor.stats else 3
        FeintService.reroll_hand(actor.meta, hand_size=hand_size)

    def _append_result_logs(
        self, ctx: BattleContext, result: InteractionResultDTO, *, action: CombatActionDTO, wave: int
    ) -> None:
        """
        Переносит полный результат резольвера и pipeline events в боевой log buffer.
        """
        ctx.pending_logs.extend(
            CombatLogBuilder.build_result_entries(
                ctx=ctx,
                result=result,
                action=action,
                wave=wave,
                timestamp=time.time(),
            )
        )

    def _append_result_support_payload(
        self, ctx: BattleContext, result: InteractionResultDTO, *, action: CombatActionDTO, wave: int
    ) -> None:
        ctx.pending_result_support_tasks.append(
            self._result_support_payload(
                ctx=ctx,
                result=result,
                action=action,
                wave=wave,
            )
        )

    @staticmethod
    def _result_support_payload(
        ctx: BattleContext,
        result: InteractionResultDTO,
        *,
        action: CombatActionDTO,
        wave: int,
    ) -> dict[str, Any]:
        return CombatResultSupportTaskDTO.from_context(
            ctx=ctx,
            result=result,
            action=action,
            wave=wave,
            seq=len(ctx.pending_result_support_tasks),
            timestamp=time.time(),
        ).model_dump(mode="json")

    @staticmethod
    def _log_result_info(ctx: BattleContext, result: InteractionResultDTO, *, wave: int) -> None:
        checks = " ".join(
            f"{CombatAnalyticsFactBuilder.STAGES.get(check.stage, check.stage)}{'✓' if check.passed else '×'}"
            for check in result.checks
        )
        log.info(
            "CombatExchange | session={} turn={} wave={} {}->{} outcome={} checks={} dmg={} heal={} events={}",
            ctx.session_id,
            ctx.meta.step_counter + 1,
            wave,
            result.source_id,
            result.target_id,
            CombatAnalyticsFactBuilder.OUTCOMES.get(CombatAnalyticsFactBuilder._outcome(result), "N"),
            checks or "-",
            result.damage_final,
            result.healing_final,
            [event.type for event in result.events],
        )

    def _collect_target_returns(self, ctx: BattleContext, action: CombatActionDTO) -> None:
        """
        Собирает пары (source_id, target_id) для возврата в очереди после Exchange.

        Логика:
        - Source всегда возвращает target в свою очередь
        - Target возвращает source в свою очередь (если был partner_move)
        - Если не было partner_move (forced attack) - target не возвращает
        """
        source_id = action.move.char_id
        target_id_raw = getattr(action.move.payload, "target_id", None)

        if not target_id_raw:
            return

        target_id = normalize_actor_id(cast("ActorIdLike", target_id_raw))

        ctx.pending_target_returns.append(self._target_return(source_id, target_id))

        # Target -> Source (только если был ответ)
        if action.partner_move:
            ctx.pending_target_returns.append(self._target_return(target_id, source_id))

    @staticmethod
    def _target_return(source_id: ActorIdLike, target_id: ActorIdLike) -> TargetReturnDTO:
        return {"source_id": normalize_actor_id(source_id), "target_id": normalize_actor_id(target_id)}

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
