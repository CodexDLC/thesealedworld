import asyncio
import time
from collections.abc import Awaitable
from typing import Any, cast

from loguru import logger as log

from src.backend.features.combat.dto.action import CombatActionDTO, CombatMoveDTO
from src.backend.features.combat.dto.actor import ActorSnapshot
from src.backend.features.combat.dto.ids import ActorId, ActorIdLike, normalize_actor_id
from src.backend.features.combat.dto.pipeline import (
    CombatEffectFactDTO,
    CombatEventDTO,
    CombatResourceApplicationDTO,
    InteractionResultDTO,
    PipelineContextDTO,
)
from src.backend.features.combat.dto.session import BattleContext, TargetReturnDTO
from src.backend.features.combat.integrations import CombatCatalogIntegrator
from src.backend.features.combat.runtime.ai.ai_memory import record_exchange_outcome
from src.backend.features.combat.runtime.engine.ability_service import AbilityService
from src.backend.features.combat.runtime.engine.feint_service import FeintService
from src.backend.features.combat.runtime.engine.pipeline import CombatPipeline
from src.backend.features.combat.runtime.engine.ranged_position import RangedPositionService
from src.backend.features.combat.runtime.engine.stats_engine import StatsEngine
from src.backend.features.combat.runtime.engine.target_resolver import TargetResolver
from src.backend.features.combat.runtime.support import (
    CombatAnalyticsFactBuilder,
    CombatLogBuilder,
    CombatResultSupportTaskDTO,
)
from src.backend.features.game_catalog.combat.resources.common.targeting import TargetType


class CombatExecutor:
    """Execute runnable combat actions inside an in-memory battle context.

    The executor is the runtime stage that owns combat action routing after
    collector matchmaking has already happened. It resolves exchange and
    unidirectional actions through ``CombatPipeline``, accumulates logs/support
    payloads, marks dead actors, and prepares target returns for commit.

    It does not fetch Redis state, acquire locks, or enqueue ARQ jobs directly.
    Those concerns stay in the executor task and integration layers.
    """

    def __init__(self):
        self.pipeline = CombatPipeline()
        self.target_resolver = TargetResolver()

    async def process_batch(self, ctx: BattleContext, actions: list[CombatActionDTO]) -> list[str]:
        """Process one executor batch against a loaded battle context.

        Args:
            ctx: Mutable in-memory battle context for the current executor run.
            actions: Runnable combat actions already prepared by the collector.

        Returns:
            List of move ids that were consumed from the action queue, even when
            individual actions failed after validation.
        """
        processed_ids = []

        for action in actions:
            try:
                await self._process_single_action(ctx, action)
                processed_ids.append(action.move.move_id)
            except Exception:  # noqa: BLE001
                log.bind(move_id=action.move.move_id).exception("ExecutorActionFailed")
                processed_ids.append(action.move.move_id)

        # Сбор мертвых акторов после обработки батча
        self._collect_dead_actors(ctx)

        return processed_ids

    async def _process_single_action(self, ctx: BattleContext, action: CombatActionDTO) -> None:
        """Route one runnable combat action into the correct executor branch."""
        if not action.move:
            log.warning("ExecutorActionMissingMoveData")
            return

        # Routing Logic
        # payload is object, use getattr
        target_id = getattr(action.move.payload, "target_id", None)

        if self._skip_stale_action_if_dead(ctx, action):
            return

        if action.action_type == "exchange" or (action.is_forced and target_id):
            await self._handle_exchange(ctx, action)
        else:
            # Instant / Item (Одностороннее воздействие)
            log.bind(
                session_id=ctx.session_id,
                move_id=action.move.move_id,
                action_type=action.action_type,
                char_id=str(action.move.char_id),
                ability_id=getattr(action.move.payload, "ability_id", None),
                target_id=str(target_id) if target_id else None,
            ).info("ExecutorHandleUnidirectional")
            await self._handle_unidirectional(ctx, action)

    def _skip_stale_action_if_dead(self, ctx: BattleContext, action: CombatActionDTO) -> bool:
        checked = [("source", action.move.char_id), ("target", getattr(action.move.payload, "target_id", None))]
        if action.partner_move:
            checked.extend(
                [
                    ("source", action.partner_move.char_id),
                    ("target", getattr(action.partner_move.payload, "target_id", None)),
                ]
            )

        for role, actor_id in checked:
            if actor_id is None:
                continue
            actor = ctx.get_actor(cast("ActorIdLike", actor_id))
            if actor and not actor.is_alive:
                self._append_stale_action_log(ctx, action, actor=actor, reason=f"{role}_dead")
                return True

        return False

    @staticmethod
    def _append_stale_action_log(
        ctx: BattleContext, action: CombatActionDTO, *, actor: ActorSnapshot, reason: str
    ) -> None:
        actor_name = actor.meta.name or str(actor.meta.id)
        text = f"{actor_name}: цель уже мертва." if reason == "target_dead" else f"{actor_name} уже мертв."
        ctx.pending_logs.append(
            {
                "type": "LOG",
                "kind": "stale_action",
                "reason": reason,
                "text": text,
                "timestamp": time.time(),
                "global_turn": ctx.meta.step_counter,
                "source_id": str(action.move.char_id),
                "target_id": str(getattr(action.move.payload, "target_id", "")),
                "actor": {
                    "id": str(actor.meta.id),
                    "name": actor_name,
                    "team": actor.meta.team,
                    "actor_type": actor.meta.type,
                },
                "tags": ["runtime", "stale_action", "dead_actor"],
            }
        )

    # ==========================================================================
    # 🌿 BRANCHES (Logic Flow)
    # ==========================================================================

    async def _handle_exchange(self, ctx: BattleContext, action: CombatActionDTO) -> None:
        """Resolve one paired or forced exchange.

        Args:
            ctx: Mutable in-memory battle context for the current batch.
            action: Exchange action that may include a partner move or be forced.

        Side Effects:
            - Applies periodic turn-start effects.
            - Resolves one or more combat waves through the pipeline.
            - Appends combat logs and support payloads.
            - Collects target returns and advances global step state.

        Runtime Contract:
            - Collector already decided pairing/force-attack semantics.
            - No Redis I/O is allowed inside this method.
        """
        source = ctx.get_actor(action.move.char_id)
        target_id = getattr(action.move.payload, "target_id", None)
        target = ctx.get_actor(cast("ActorIdLike", target_id)) if target_id else None

        if not source or not target:
            log.bind(char_id=action.move.char_id, target_id=target_id).warning("ExecutorExchangeParticipantsMissing")
            return

        self._process_periodic_effects(ctx, [source, target], action=action, wave=0)

        # Очередь расчетов (Waves). Actor ids are resolved into fresh snapshots
        # at each wave so one result cannot leak mutations into its partner.
        pending_tasks: list[tuple[ActorId, ActorId | None, CombatMoveDTO, dict[str, Any], bool]] = []

        # 1. Main Attack (A -> B)
        pending_tasks.append((source.char_id, target.char_id, action.move, {"action_mode": "exchange"}, False))

        # 2. Partner Attack (B -> A)
        if action.partner_move:
            pending_tasks.append(
                (
                    target.char_id,
                    source.char_id,
                    action.partner_move,
                    {"action_mode": "exchange"},
                    False,
                )
            )
        elif not action.is_forced:
            log.error("ExecutorExchangePartnerMissing")
            return

        secondary_targets, secondary_damage_mult = self._secondary_feint_plan(
            ctx, action, primary_target_id=normalize_actor_id(cast("ActorIdLike", target_id))
        )
        for secondary_target in secondary_targets:
            pending_tasks.append(
                (
                    source.char_id,
                    secondary_target.char_id,
                    action.move,
                    {
                        "action_mode": "unidirectional",
                        "damage_mult": secondary_damage_mult,
                        "feint_role": "secondary",
                        "pay_cost": False,
                        "generate_feints": False,
                    },
                    True,
                )
            )

        # --- EXECUTION LOOP (Waves) ---
        max_waves = 3
        wave = 0
        used_feints: dict[tuple[str, str], ActorSnapshot] = {}

        while pending_tasks and wave < max_waves:
            wave += 1

            # Запускаем текущую волну по sandbox snapshots текущего состояния.
            current_tasks = pending_tasks
            runnable: list[
                tuple[Awaitable[InteractionResultDTO], ActorSnapshot, ActorSnapshot | None, CombatMoveDTO, bool]
            ] = []
            for source_id, target_task_id, move, mods, is_secondary in current_tasks:
                real_source = ctx.get_actor(source_id)
                real_target = ctx.get_actor(target_task_id) if target_task_id is not None else None
                if not real_source or (target_task_id is not None and not real_target):
                    continue
                calc_source = real_source.model_copy(deep=True)
                calc_target = real_target.model_copy(deep=True) if real_target else None
                runnable.append(
                    (
                        self._create_task(calc_source, calc_target, move, mods=mods),
                        real_source,
                        real_target,
                        move,
                        is_secondary,
                    )
                )
            results = await asyncio.gather(*(task for task, _source, _target, _move, _is_secondary in runnable))
            pending_tasks = []

            for result, (_task, real_source, real_target, _move, is_secondary) in zip(results, runnable, strict=False):
                if not is_secondary:
                    self._append_cleave_splash(ctx, result, real_source, real_target)

            commit_pairs = [
                (real_source, real_target, result)
                for result, (_task, real_source, real_target, _move, _is_secondary) in zip(
                    results, runnable, strict=False
                )
            ]
            commit_ctx = PipelineContextDTO()
            commit_ctx.flags.meta.action_mode = "exchange"
            commit_ctx.flags.meta.grant_exchange_gift = True
            self.pipeline.mechanics_service.apply_exchange_results(
                commit_ctx,
                commit_pairs,
                actors_by_id={str(actor_id): actor for actor_id, actor in ctx.actors.items()},
            )
            RangedPositionService.update_after_exchange(commit_pairs)

            for result, (_task, _real_source, _real_target, move, is_secondary) in zip(
                results,
                runnable,
                strict=False,
            ):
                result_action = self._action_for_move(action, move, result=result)
                s_id = result.source_id
                t_id = result.target_id

                log.bind(
                    source_id=s_id,
                    target_id=t_id,
                    hand=result.hand,
                    outcome=self._result_outcome(result),
                    is_hit=result.is_hit,
                    is_crit=result.is_crit,
                    damage_final=result.damage_final,
                    healing_final=result.healing_final,
                    events=[event.type for event in result.events],
                ).trace("ExecutorResult")
                self._append_result_logs(ctx, result, action=result_action, wave=wave)
                self._append_result_support_payload(ctx, result, action=result_action, wave=wave)
                self._log_result_info(ctx, result, wave=wave)
                self._refund_feint_cost_if_needed(ctx, result, move)
                if not is_secondary and not result.chain_events.preserve_feint:
                    feint_id = getattr(move.payload, "feint_id", None)
                    if feint_id:
                        used_feints[(str(real_source.char_id), str(feint_id))] = real_source
                if s_id is None or t_id is None:
                    log.warning("ExecutorResultActorIdsMissing")
                    continue

                # Cross-turn AI memory hook: observe one (attacker, defender,
                # outcome, feint) tuple per resolved exchange. Read-only side
                # is the AI runtime; this is the only writer.
                if not is_secondary:
                    record_exchange_outcome(
                        ctx,
                        s_id,
                        t_id,
                        self._result_outcome(result),
                        getattr(move.payload, "feint_id", None),
                    )

                # --- CHAIN REACTIONS ---
                if is_secondary:
                    continue

                # 1. Counter-Attack
                if result.chain_events.trigger_counter_attack:
                    defender = ctx.get_actor(t_id)
                    attacker = ctx.get_actor(s_id)

                    if defender and attacker and defender.is_alive and attacker.is_alive:
                        log.bind(source_id=t_id, target_id=s_id).trace("ExecutorCounterAttackTriggered")
                        counter_move = action.partner_move if action.partner_move else action.move
                        pending_tasks.append(
                            (
                                defender.char_id,
                                attacker.char_id,
                                counter_move,
                                {"is_counter_attack": True, "action_mode": "exchange"},
                                False,
                            )
                        )

                # 2. Off-Hand Attack
                if result.chain_events.trigger_offhand_attack:
                    attacker = ctx.get_actor(s_id)
                    defender = ctx.get_actor(t_id)

                    if attacker and defender and attacker.is_alive and defender.is_alive:
                        log.bind(source_id=s_id, target_id=t_id).trace("ExecutorOffHandAttackTriggered")
                        pending_tasks.append(
                            (
                                attacker.char_id,
                                defender.char_id,
                                action.move,
                                {"hand": "off", "action_mode": "exchange"},
                                False,
                            )
                        )

        # --- FINALIZE ---
        source.meta.exchange_counter += 1
        target.meta.exchange_counter += 1
        ctx.meta.step_counter += 1
        self._cleanup_finished_control_effects(ctx, [source, target], action=action, wave=wave)

        self._apply_used_feint_cooldowns(used_feints)
        self._reroll_exchange_feints(source)
        self._reroll_exchange_feints(target)

        # НОВОЕ: Собираем пары для возврата целей
        self._collect_target_returns(ctx, action)

        log.bind(wave_count=wave, global_step=ctx.meta.step_counter).trace("ExecutorExchangeCompleted")

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
        """Resolve an item/instant/system-style one-way action."""
        source = ctx.get_actor(action.move.char_id)
        if not source:
            return

        self._process_periodic_effects(ctx, [source], action=action, wave=0)

        target_ids = action.move.targets or []
        if not target_ids:
            target_ids = self._resolve_unidirectional_targets(ctx, action)
            action.move.targets = list(target_ids)

        # Check for self target in payload
        payload_target = getattr(action.move.payload, "target_id", None)
        if action.move.strategy == "item" and payload_target == "self":
            target_ids = [source.char_id]

        tasks: list[Awaitable[InteractionResultDTO]] = []
        task_sources: list[tuple[ActorSnapshot, ActorSnapshot, CombatMoveDTO, dict[str, Any]]] = []
        mods = self._unidirectional_mods(action)
        for tid in target_ids:
            target = ctx.get_actor(tid)
            if target:
                tasks.append(self._create_task(source, target, action.move, mods=mods))
                task_sources.append((source, target, action.move, mods))

        if tasks:
            results = await asyncio.gather(*tasks)
            is_grouped_area_log = CombatLogBuilder._is_area_action(action) and len(results) > 1
            for result, (_source, target_snapshot, _move, _mods) in zip(results, task_sources, strict=False):
                target = ctx.get_actor(result.target_id) if result.target_id is not None else None
                self._append_cleave_splash(ctx, result, source, target_snapshot)
                commit_ctx = PipelineContextDTO()
                commit_ctx.flags.meta.action_mode = "unidirectional"
                commit_ctx.flags.meta.grant_exchange_gift = False
                self.pipeline.mechanics_service.apply_interaction_result(
                    commit_ctx,
                    source,
                    target,
                    result,
                    actors_by_id={str(actor_id): actor for actor_id, actor in ctx.actors.items()},
                )
                if not is_grouped_area_log:
                    self._append_result_logs(ctx, result, action=action, wave=1)
                self._append_result_support_payload(ctx, result, action=action, wave=1)
                self._log_result_info(ctx, result, wave=1)
            if is_grouped_area_log:
                self._append_area_result_log(ctx, results, action=action, wave=1)
            self._apply_unidirectional_ability_cooldown(source, action, results)
            log.bind(target_count=len(tasks)).info("ExecutorUnidirectionalCompleted")

    # ==========================================================================
    # 🛠️ HELPERS
    # ==========================================================================

    def _resolve_unidirectional_targets(self, ctx: BattleContext, action: CombatActionDTO) -> list[ActorId]:
        raw_target = getattr(action.move.payload, "target_id", None)
        ability_id = getattr(action.move.payload, "ability_id", None)
        if ability_id:
            entry = CombatCatalogIntegrator.get_ability_catalog_entry(str(ability_id))
            if entry is not None:
                ability = entry.technical
                target_count = max(1, int(getattr(ability, "target_count", 1) or 1))
                if str(ability.target) == "random_enemy" and target_count > 1:
                    raw_target = f"random_enemy_{target_count}"
                elif str(ability.target) == "all_enemies":
                    raw_target = "all_enemies"
                elif str(ability.target) == "self":
                    raw_target = "self"
        return self.target_resolver.resolve(action.move.char_id, raw_target, ctx.meta)

    def _create_task(
        self,
        source: ActorSnapshot,
        target: ActorSnapshot | None,
        move: CombatMoveDTO,
        mods: dict[str, Any] | None = None,
    ) -> Awaitable[InteractionResultDTO]:
        """Create one pipeline calculation task for a concrete source/target pair."""
        return self.pipeline.calculate(
            source=source,
            target=target,
            move=move,
            external_mods=mods,
            exchange_count=source.meta.exchange_counter,
        )

    def _secondary_feint_plan(
        self, ctx: BattleContext, action: CombatActionDTO, *, primary_target_id: ActorId
    ) -> tuple[list[ActorSnapshot], float]:
        feint_id = getattr(action.move.payload, "feint_id", None)
        if not feint_id:
            return [], 0.5

        feint_entry = CombatCatalogIntegrator.get_feint_catalog_entry(str(feint_id))
        if not feint_entry:
            return [], 0.5
        feint_config = feint_entry.technical
        if feint_config.target != TargetType.ALL_ENEMIES or feint_config.target_count <= 1:
            return [], 0.5

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
        return selected, max(0.0, float(getattr(feint_config, "secondary_damage_mult", 0.5) or 0.5))

    @staticmethod
    def _unidirectional_mods(action: CombatActionDTO) -> dict[str, Any]:
        mods: dict[str, Any] = {"action_mode": "unidirectional"}
        ability_id = getattr(action.move.payload, "ability_id", None)
        if not ability_id:
            return mods
        entry = CombatCatalogIntegrator.get_ability_catalog_entry(str(ability_id))
        if entry is None:
            return mods
        ability = entry.technical
        if int(getattr(ability, "target_count", 1) or 1) > 1:
            mods["damage_mult"] = max(0.0, float(getattr(ability, "secondary_damage_mult", 1.0) or 1.0))
        return mods

    @staticmethod
    def _apply_unidirectional_ability_cooldown(
        source: ActorSnapshot,
        action: CombatActionDTO,
        results: list[InteractionResultDTO],
    ) -> None:
        ability_id = getattr(action.move.payload, "ability_id", None)
        if not ability_id:
            return
        if any(result.action_facts.get("id") == ability_id and not result.skip_reason for result in results):
            AbilityService.apply_ability_cooldown(source, str(ability_id))

    def _append_cleave_splash(
        self,
        ctx: BattleContext,
        result: InteractionResultDTO,
        source: ActorSnapshot,
        primary_target: ActorSnapshot | None,
    ) -> None:
        if not source.is_alive:
            return
        if not result.is_hit or result.damage_final <= 0:
            return

        StatsEngine.ensure_stats(source)
        if source.stats is None:
            return
        damage_mult = max(0.0, float(source.stats.mods.cleave_damage_mult or 0.0))
        target_count = max(0, int(source.stats.mods.cleave_target_count or 0))
        if damage_mult <= 0 or target_count <= 0:
            return

        damage = int(result.damage_final * damage_mult)
        if damage <= 0:
            return

        excluded = {str(source.char_id)}
        if primary_target is not None:
            excluded.add(str(primary_target.char_id))
        selected: list[ActorSnapshot] = []
        for target_id in self.target_resolver.resolve(source.char_id, TargetType.ALL_ENEMIES.value, ctx.meta):
            if str(target_id) in excluded:
                continue
            target = ctx.get_actor(target_id)
            if target and target.is_alive:
                selected.append(target)
            if len(selected) >= target_count:
                break

        for target in selected:
            result.resource_applications.append(
                CombatResourceApplicationDTO(
                    actor_id=target.char_id,
                    owner="other",
                    resource="hp",
                    reason="cleave_splash",
                    value=f"-{damage}",
                    source_effect_id="cleave",
                    tags=["cleave", "splash"],
                )
            )
            result.events.append(
                CombatEventDTO(
                    type="HIT",
                    source_id=source.char_id,
                    target_id=target.char_id,
                    value=damage,
                    resource="hp",
                    action_id="cleave_splash",
                    tags=["CLEAVE", "SPLASH"],
                )
            )

    def _process_periodic_effects(
        self, ctx: BattleContext, actors: list[Any], *, action: CombatActionDTO, wave: int
    ) -> None:
        """Apply turn-start periodic effects before the main action branch resolves."""
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

    def _cleanup_finished_control_effects(
        self, ctx: BattleContext, actors: list[ActorSnapshot], *, action: CombatActionDTO, wave: int
    ) -> None:
        """Remove effects that expired on the actor's own exchange counter."""
        seen: set[ActorId] = set()
        for actor in actors:
            actor_id = actor.char_id
            if actor_id in seen:
                continue
            seen.add(actor_id)
            expired = [
                effect for effect in actor.statuses.effects if effect.expire_at_exchange <= actor.meta.exchange_counter
            ]
            if not expired:
                continue
            AbilityService._cleanup_expired_effects_pre_calc(actor)
            result = InteractionResultDTO(source_id=action.move.char_id, target_id=actor.char_id)
            for effect in expired:
                effect_entry = CombatCatalogIntegrator.get_effect_catalog_entry(effect.effect_id)
                tags = set(effect_entry.technical.tags) if effect_entry else set()
                result.effect_facts.append(
                    CombatEffectFactDTO(
                        actor_id=actor.char_id,
                        owner="target",
                        effect_id=effect.effect_id,
                        action="expire",
                        source_effect_id=effect.effect_id,
                        tags=sorted(tags),
                    )
                )
            ctx.pending_logs.extend(
                CombatLogBuilder.build_effect_fact_entries(
                    ctx=ctx,
                    result=result,
                    action=action,
                    wave=wave,
                    timestamp=time.time(),
                )
            )

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
            log.bind(feint_id=feint_id).warning("ExecutorFeintRefundFailed")
            return

        feint_config = feint_entry.technical
        FeintService.refund_cost(source.meta, dict(feint_config.cost.tactics))

    @staticmethod
    def _reroll_exchange_feints(actor) -> None:
        hand_size = actor.stats.mods.hand_size if actor.stats else 3
        active_effect_ids = {
            effect.effect_id
            for effect in actor.statuses.effects
            if effect.expire_at_exchange > actor.meta.exchange_counter
        }
        FeintService.reroll_hand(actor.meta, hand_size=hand_size, active_effect_ids=active_effect_ids)

    @staticmethod
    def _apply_used_feint_cooldowns(used_feints: dict[tuple[str, str], ActorSnapshot]) -> None:
        for (_actor_id, feint_id), actor in used_feints.items():
            feint_entry = CombatCatalogIntegrator.get_feint_catalog_entry(feint_id)
            if feint_entry is None:
                continue
            cooldown = sum(max(0, int(amount)) for amount in feint_entry.technical.cost.tactics.values())
            FeintService.apply_cooldown(actor.meta, feint_id, cooldown)

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

    def _append_area_result_log(
        self, ctx: BattleContext, results: list[InteractionResultDTO], *, action: CombatActionDTO, wave: int
    ) -> None:
        entry = CombatLogBuilder.build_area_result_entry(
            ctx=ctx,
            results=results,
            action=action,
            wave=wave,
            timestamp=time.time(),
        )
        if entry is not None:
            ctx.pending_logs.append(entry)

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
        log.bind(
            session_id=ctx.session_id,
            turn=ctx.meta.step_counter + 1,
            wave=wave,
            source_id=result.source_id,
            target_id=result.target_id,
            outcome=CombatAnalyticsFactBuilder.OUTCOMES.get(CombatAnalyticsFactBuilder._outcome(result), "N"),
            checks=checks or "-",
            damage=result.damage_final,
            healing=result.healing_final,
            events=[event.type for event in result.events],
        ).trace("CombatExchange")

    def _collect_target_returns(self, ctx: BattleContext, action: CombatActionDTO) -> None:
        """Collect target queue return pairs after a resolved exchange.

        Source regains the target when both survive. The defending target also
        regains the source only when a partner move existed.
        """
        source_id = action.move.char_id
        target_id_raw = getattr(action.move.payload, "target_id", None)

        if not target_id_raw:
            return

        target_id = normalize_actor_id(cast("ActorIdLike", target_id_raw))

        if self._can_return_target(ctx, source_id, target_id):
            ctx.pending_target_returns.append(self._target_return(source_id, target_id))

        # Target -> Source (только если был ответ)
        if action.partner_move and self._can_return_target(ctx, target_id, source_id):
            ctx.pending_target_returns.append(self._target_return(target_id, source_id))

    @staticmethod
    def _target_return(source_id: ActorIdLike, target_id: ActorIdLike) -> TargetReturnDTO:
        return {"source_id": normalize_actor_id(source_id), "target_id": normalize_actor_id(target_id)}

    @staticmethod
    def _can_return_target(ctx: BattleContext, source_id: ActorIdLike, target_id: ActorIdLike) -> bool:
        source = ctx.get_actor(source_id)
        target = ctx.get_actor(target_id)
        return bool(source and source.is_alive and target and target.is_alive)

    def _collect_dead_actors(self, ctx: BattleContext) -> None:
        """Collect newly dead actors so commit can update battle meta."""
        for char_id, actor in ctx.actors.items():
            if actor.meta.hp <= 0:
                actor.meta.is_dead = True
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
