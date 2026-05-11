from typing import Literal

# === НОВЫЙ ИМПОРТ ===
from src.backend.core.calculators.stats_waterfall_calculator import StatsWaterfallCalculator
from src.backend.features.combat.dto import (
    ActorSnapshot,
    CombatDeathFactDTO,
    CombatEffectFactDTO,
    CombatEventDTO,
    CombatResourceFactDTO,
    CombatTokenFactDTO,
    InteractionResultDTO,
    PipelineContextDTO,
)
from src.backend.features.combat.runtime.engine.feint_service import FeintService


class MechanicsService:
    """
    Сервис мутации состояния (State Mutation).
    Отвечает за изменение HP, Energy, Tokens и регистрацию XP.
    Использует StatsWaterfallCalculator для расчета дельты ресурсов.
    """

    # ==============================================================================
    # PUBLIC INTERFACE
    # ==============================================================================

    def process_turn_start(self, ctx: PipelineContextDTO, actor: ActorSnapshot) -> None:
        """
        Обработка начала хода: Тики эффектов (DOT/HOT).
        """
        # Проверка флага: применять ли периодические эффекты
        if ctx.flags.mechanics.apply_periodic:
            # 1. Collect Ticks
            hp_changes = []
            en_changes = []
            hp_effect_ids = []
            en_effect_ids = []

            for effect in actor.statuses.effects:
                if not effect.impact:
                    continue

                # HP Impact
                if "hp" in effect.impact:
                    val = effect.impact["hp"]
                    hp_changes.append(str(val))
                    hp_effect_ids.append(effect.effect_id)
                    self._log_effect_tick(ctx, actor, effect.effect_id, val, "hp")

                # EN Impact
                if "en" in effect.impact:
                    val = effect.impact["en"]
                    en_changes.append(str(val))
                    en_effect_ids.append(effect.effect_id)
                    self._log_effect_tick(ctx, actor, effect.effect_id, val, "en")

            # 2. Apply Changes
            if hp_changes:
                applied = self._apply_resource_delta(actor, "hp", hp_changes)
                self._record_resource_fact(
                    ctx.result,
                    actor=actor,
                    owner="self",
                    resource="hp",
                    reason="effect_tick",
                    applied=applied,
                    source_effect_id=hp_effect_ids[0] if len(hp_effect_ids) == 1 else None,
                    tags=hp_effect_ids,
                )
            if en_changes:
                applied = self._apply_resource_delta(actor, "en", en_changes)
                self._record_resource_fact(
                    ctx.result,
                    actor=actor,
                    owner="self",
                    resource="en",
                    reason="effect_tick",
                    applied=applied,
                    source_effect_id=en_effect_ids[0] if len(en_effect_ids) == 1 else None,
                    tags=en_effect_ids,
                )

            if actor.meta.hp <= 0 and not actor.meta.is_dead:
                actor.meta.is_dead = True
                ctx.result.death_facts.append(
                    CombatDeathFactDTO(actor_id=actor.char_id, owner="self", reason="effect_tick")
                )
                ctx.result.events.append(
                    CombatEventDTO(
                        type="DEATH",
                        source_id=actor.char_id,
                        target_id=actor.char_id,
                        value=0,
                    )
                )

    def apply_interaction_result(
        self, ctx: PipelineContextDTO, source: ActorSnapshot, target: ActorSnapshot | None, result: InteractionResultDTO
    ) -> None:
        """
        Применение результатов боя (Урон, Косты, Токены, XP).
        """
        # 1. [SOURCE] Apply Costs & Tokens
        self._apply_source_changes(ctx, source, result)

        # 2. [TARGET] Apply Damage
        if target:
            self._apply_target_changes(ctx, target, result)

        # 3. [XP] Register Events
        self._register_xp_events(ctx, source, target, result)

        # 4. [FEINTS] One-way actions can still refill locally. Exchange hands are
        # rerolled once in CombatExecutor after the full paired exchange resolves.
        if ctx.flags.mechanics.generate_feints and ctx.flags.meta.action_mode == "unidirectional":
            # Получаем размер руки из статов (если есть) или дефолт 3
            source_hand = source.stats.mods.hand_size if source.stats else 3
            FeintService.refill_hand(source.meta, hand_size=source_hand)

            if target:
                target_hand = target.stats.mods.hand_size if target.stats else 3
                FeintService.refill_hand(target.meta, hand_size=target_hand)

    # ==============================================================================
    # INTERNAL LOGIC
    # ==============================================================================

    def _apply_source_changes(
        self, ctx: PipelineContextDTO, source: ActorSnapshot, result: InteractionResultDTO
    ) -> None:
        """
        Изменения для Атакующего: Косты, Токены.
        """
        # A. Costs (из resource_changes)
        if ctx.flags.mechanics.pay_cost:
            hp_changes = []
            en_changes = []

            # Пример: {"hp": {"cost": "-10"}, "en": {"cost": "-20"}}
            if "hp" in result.resource_changes:
                hp_changes.extend(result.resource_changes["hp"].items())

            if "en" in result.resource_changes:
                en_changes.extend(result.resource_changes["en"].items())

            # Apply Costs
            if hp_changes:
                applied = self._apply_resource_delta(source, "hp", [val for _key, val in hp_changes])
                self._record_resource_fact(
                    result,
                    actor=source,
                    owner="source",
                    resource="hp",
                    reason=self._resource_change_reason(hp_changes),
                    applied=applied,
                )
            if en_changes:
                applied = self._apply_resource_delta(source, "en", [val for _key, val in en_changes])
                self._record_resource_fact(
                    result,
                    actor=source,
                    owner="source",
                    resource="en",
                    reason=self._resource_change_reason(en_changes),
                    applied=applied,
                )

        # B. Tokens Awarded (Всегда начисляем, если не сказано иное? Пока оставим безусловно)
        if result.tokens_awarded_attacker:
            for token, amount in result.tokens_awarded_attacker.items():
                before = source.meta.tokens.get(token, 0)
                source.meta.tokens[token] = source.meta.tokens.get(token, 0) + amount
                result.token_facts.append(
                    CombatTokenFactDTO(
                        actor_id=source.char_id,
                        owner="source",
                        token=token,
                        amount=amount,
                        before=before,
                        after=source.meta.tokens[token],
                        reason="award",
                    )
                )

        # C. Reflected damage from defender-side block style.
        if ctx.flags.mechanics.apply_damage and result.reflected_damage > 0:
            applied = self._apply_resource_delta(source, "hp", [f"-{result.reflected_damage}"])
            self._record_resource_fact(
                result,
                actor=source,
                owner="source",
                resource="hp",
                reason="reflect",
                applied=applied,
                tags=["REFLECT"],
            )
            ctx.result.events.append(
                CombatEventDTO(
                    type="HIT",
                    source_id=result.target_id or source.char_id,
                    target_id=source.char_id,
                    value=result.reflected_damage,
                    resource="hp",
                    tags=["REFLECT"],
                )
            )

            if ctx.flags.mechanics.check_death and source.meta.hp <= 0:
                source.meta.is_dead = True
                ctx.result.death_facts.append(
                    CombatDeathFactDTO(actor_id=source.char_id, owner="source", reason="reflect")
                )
                ctx.result.events.append(
                    CombatEventDTO(
                        type="DEATH",
                        source_id=source.char_id,
                        target_id=source.char_id,
                        value=0,
                    )
                )

    def _apply_target_changes(
        self, ctx: PipelineContextDTO, target: ActorSnapshot, result: InteractionResultDTO
    ) -> None:
        """
        Изменения для Защитника: Урон, защитные токены.
        """
        # A. Damage Final
        if ctx.flags.mechanics.apply_damage:
            hp_sources = []
            if result.damage_final > 0:
                hp_sources.append(f"-{result.damage_final}")

            # Apply
            if hp_sources:
                applied = self._apply_resource_delta(target, "hp", hp_sources)
                self._record_resource_fact(
                    result,
                    actor=target,
                    owner="target",
                    resource="hp",
                    reason="damage",
                    applied=applied,
                )

        # B. Death Check
        if ctx.flags.mechanics.check_death and target.meta.hp <= 0:
            target.meta.is_dead = True
            ctx.result.death_facts.append(CombatDeathFactDTO(actor_id=target.char_id, owner="target", reason="damage"))

            # Log Death Event
            ctx.result.events.append(
                CombatEventDTO(
                    type="DEATH",
                    source_id=target.char_id,
                    target_id=target.char_id,
                    value=0,
                )
            )

        # C. Tokens Awarded
        if result.tokens_awarded_defender:
            for token, amount in result.tokens_awarded_defender.items():
                before = target.meta.tokens.get(token, 0)
                target.meta.tokens[token] = target.meta.tokens.get(token, 0) + amount
                result.token_facts.append(
                    CombatTokenFactDTO(
                        actor_id=target.char_id,
                        owner="target",
                        token=token,
                        amount=amount,
                        before=before,
                        after=target.meta.tokens[token],
                        reason="award",
                    )
                )

    def _apply_resource_delta(
        self, actor: ActorSnapshot, resource: str, sources: list[str]
    ) -> tuple[int, int, int, int] | None:
        """
        Универсальный метод изменения ресурса через StatsWaterfallCalculator.
        """
        before, max_value = self._resource_state(actor, resource)
        if before is None or max_value is None:
            return None

        # 1. Calculate Delta
        delta, _ = StatsWaterfallCalculator.evaluate_sources(sources, base_value=0.0)
        delta_int = int(delta)

        if delta_int == 0:
            return None

        # 2. Apply & Clamp
        if resource == "hp":
            new_val = actor.meta.hp + delta_int
            actor.meta.hp = max(0, min(new_val, actor.meta.max_hp))
        elif resource == "en":
            new_val = actor.meta.en + delta_int
            actor.meta.en = max(0, min(new_val, actor.meta.max_en))
        else:
            return None

        after, _max_value = self._resource_state(actor, resource)
        if after is None:
            return None
        return before, after, max_value, after - before

    @staticmethod
    def _resource_state(actor: ActorSnapshot, resource: str) -> tuple[int | None, int | None]:
        if resource == "hp":
            return actor.meta.hp, actor.meta.max_hp
        if resource == "en":
            return actor.meta.en, actor.meta.max_en
        return None, None

    @staticmethod
    def _resource_change_reason(changes: list[tuple[str, str]]) -> str:
        reasons = [key for key, _value in changes]
        if len(reasons) == 1:
            return reasons[0]
        if reasons and all(reason == reasons[0] for reason in reasons):
            return reasons[0]
        return "mixed"

    @staticmethod
    def _record_resource_fact(
        result: InteractionResultDTO,
        *,
        actor: ActorSnapshot,
        owner: Literal["source", "target", "self", "other"],
        resource: str,
        reason: str,
        applied: tuple[int, int, int, int] | None,
        source_effect_id: str | None = None,
        source_trigger_id: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        if applied is None:
            return
        before, after, max_value, delta = applied
        result.resource_facts.append(
            CombatResourceFactDTO(
                actor_id=actor.char_id,
                owner=owner,
                resource=resource,
                reason=reason,
                delta=delta,
                before=before,
                after=after,
                max=max_value,
                source_effect_id=source_effect_id,
                source_trigger_id=source_trigger_id,
                tags=tags or [],
            )
        )

    def _register_xp_events(
        self,
        ctx: PipelineContextDTO,
        source: ActorSnapshot,
        target: ActorSnapshot | None,
        result: InteractionResultDTO,
    ) -> None:
        """
        Регистрация событий для XP Buffer.
        """
        if not ctx.flags.mechanics.grant_xp:
            return

        source_prefix = "off_hand" if result.hand == "off_hand" else "main_hand"

        # 1. Generic Actions
        if result.is_hit:
            self._inc_xp(source, f"{source_prefix}_hit")
        elif result.is_miss:
            self._inc_xp(source, f"{source_prefix}_miss")

        if result.is_crit:
            self._inc_xp(source, f"{source_prefix}_crit")

        # 2. Target Reactions
        if target:
            if result.is_dodged:
                self._inc_xp(target, "defense_dodge")
            if result.is_parried:
                self._inc_xp(target, "defense_parry")
            if result.is_blocked:
                self._inc_xp(target, "defense_block")

            # 3. Kill
            if target.meta.is_dead:
                self._inc_xp(source, "kill_generic")

    def _inc_xp(self, actor: ActorSnapshot, key: str, amount: float = 1.0) -> None:
        actor.xp_buffer[key] = actor.xp_buffer.get(key, 0) + amount

    def _log_effect_tick(
        self, ctx: PipelineContextDTO, actor: ActorSnapshot, effect_id: str, value: int, resource: str
    ) -> None:
        """
        Формирует лог тика эффекта.
        """
        ctx.result.effect_facts.append(
            CombatEffectFactDTO(
                actor_id=actor.char_id,
                owner="self",
                effect_id=effect_id,
                action="tick",
                value=value,
                resource=resource,
            )
        )

        # Создаем событие TICK
        event = CombatEventDTO(
            type="TICK",
            source_id=actor.char_id,  # Тот, на ком эффект
            target_id=actor.char_id,
            action_id=effect_id,
            value=value,
            resource=resource,
        )
        ctx.result.events.append(event)
