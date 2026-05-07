# === НОВЫЙ ИМПОРТ ===
from src.backend.core.calculators.stats_waterfall_calculator import StatsWaterfallCalculator
from src.backend.features.combat.dto import (
    ActorSnapshot,
    CombatEventDTO,
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

            for effect in actor.statuses.effects:
                if not effect.impact:
                    continue

                # HP Impact
                if "hp" in effect.impact:
                    val = effect.impact["hp"]
                    hp_changes.append(str(val))
                    self._log_effect_tick(ctx, actor, effect.effect_id, val, "hp")

                # EN Impact
                if "en" in effect.impact:
                    val = effect.impact["en"]
                    en_changes.append(str(val))
                    self._log_effect_tick(ctx, actor, effect.effect_id, val, "en")

            # 2. Apply Changes
            if hp_changes:
                self._apply_resource_delta(actor, "hp", hp_changes)
            if en_changes:
                self._apply_resource_delta(actor, "en", en_changes)

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

        # === НОВАЯ ИНТЕГРАЦИЯ: Пополнение руки финтов ===
        # 4. [FEINTS] Refill Hand (только для exchange, не для insta_skill)
        if ctx.flags.mechanics.generate_feints:
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
            hp_sources = []
            en_sources = []

            # Пример: {"hp": {"cost": "-10"}, "en": {"cost": "-20"}}
            if "hp" in result.resource_changes:
                for _key, val in result.resource_changes["hp"].items():
                    hp_sources.append(val)

            if "en" in result.resource_changes:
                for _key, val in result.resource_changes["en"].items():
                    en_sources.append(val)

            # Apply Costs
            if hp_sources:
                self._apply_resource_delta(source, "hp", hp_sources)
            if en_sources:
                self._apply_resource_delta(source, "en", en_sources)

        # B. Tokens Awarded (Всегда начисляем, если не сказано иное? Пока оставим безусловно)
        if result.tokens_awarded_attacker:
            for token, amount in result.tokens_awarded_attacker.items():
                source.meta.tokens[token] = source.meta.tokens.get(token, 0) + amount

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
                self._apply_resource_delta(target, "hp", hp_sources)

        # B. Death Check
        if ctx.flags.mechanics.check_death and target.meta.hp <= 0:
            target.meta.is_dead = True

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
                target.meta.tokens[token] = target.meta.tokens.get(token, 0) + amount

    def _apply_resource_delta(self, actor: ActorSnapshot, resource: str, sources: list[str]) -> None:
        """
        Универсальный метод изменения ресурса через StatsWaterfallCalculator.
        """
        # 1. Calculate Delta
        delta, _ = StatsWaterfallCalculator.evaluate_sources(sources, base_value=0.0)
        delta_int = int(delta)

        if delta_int == 0:
            return

        # 2. Apply & Clamp
        if resource == "hp":
            new_val = actor.meta.hp + delta_int
            actor.meta.hp = max(0, min(new_val, actor.meta.max_hp))
        elif resource == "en":
            new_val = actor.meta.en + delta_int
            actor.meta.en = max(0, min(new_val, actor.meta.max_en))

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

        # 1. Generic Actions
        if result.is_hit:
            self._inc_xp(source, "action_hit")
        elif result.is_miss:
            self._inc_xp(source, "action_miss")

        if result.is_crit:
            self._inc_xp(source, "action_crit")

        # 2. Skill Usage (TODO: Pass move to get ID)

        # 3. Target Reactions
        if target:
            if result.is_dodged:
                self._inc_xp(target, "reaction_dodge")
            if result.is_parried:
                self._inc_xp(target, "reaction_parry")
            if result.is_blocked:
                self._inc_xp(target, "reaction_block")

            # 4. Kill
            if target.meta.is_dead:
                self._inc_xp(source, "kill_generic")

    def _inc_xp(self, actor: ActorSnapshot, key: str, amount: int = 1) -> None:
        actor.xp_buffer[key] = actor.xp_buffer.get(key, 0) + amount

    def _log_effect_tick(
        self, ctx: PipelineContextDTO, actor: ActorSnapshot, effect_id: str, value: int, resource: str
    ) -> None:
        """
        Формирует лог тика эффекта.
        """
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
