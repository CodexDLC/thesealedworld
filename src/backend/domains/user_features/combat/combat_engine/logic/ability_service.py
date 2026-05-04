import uuid
from typing import Any, Literal

from loguru import logger as log

from src.backend.domains.user_features.combat.combat_engine.logic.effect_factory import EffectFactory
from src.backend.domains.user_features.combat.dto import (
    ActiveAbilityDTO,
    ActorSnapshot,
    CombatEventDTO,
    CombatMoveDTO,
    ExchangePayload,
    InstantPayload,
    PipelineContextDTO,
)
from src.backend.resources.game_data import GameData
from src.backend.resources.game_data.abilities.presets import PIPELINE_PRESETS
from src.backend.resources.game_data.abilities.schemas import AbilityConfigDTO, AbilityCostDTO
from src.backend.resources.game_data.feints.schemas import FeintConfigDTO


class AbilityService:
    """
    Универсальный обработчик способностей (Abilities) и финтов (Feints).
    Архитектура: Оркестратор -> Роутер -> Атомарные методы.
    """

    # ==============================================================================
    # PUBLIC INTERFACE (ORCHESTRATOR)
    # ==============================================================================

    def pre_process(
        self,
        ctx: PipelineContextDTO,
        move: CombatMoveDTO,
        source: ActorSnapshot,
        target: ActorSnapshot | None = None,
    ) -> None:
        """
        Pre-Calc этап: Подготовка контекста, проверка статусов, применение мутаций.
        """
        # 1. [CLEANUP EXPIRED EFFECTS]
        AbilityService._cleanup_expired_effects_pre_calc(source)
        if target:
            AbilityService._cleanup_expired_effects_pre_calc(target)

        # 2. [SOURCE STATUS CHECK]
        self._apply_status_effects(ctx, source, mode="source")

        # 3. [TARGET STATUS CHECK]
        if target:
            self._apply_status_effects(ctx, target, mode="target")

        # 4. [ROUTING & LOGIC]
        if ctx.phases.run_calculator:
            # Строгая типизация извлечения ID
            ability_id = self._extract_action_id(move, mode="ability")
            feint_id = self._extract_action_id(move, mode="feint")

            if ability_id:
                self._process_action_logic(ctx, move, source, target, mode="ability")
            elif feint_id:
                self._process_action_logic(ctx, move, source, target, mode="feint")
            else:
                # Basic Attack (No CAST event needed? Or maybe "ATTACK"?)
                pass
        else:
            pass

    def post_process(
        self,
        ctx: PipelineContextDTO,
        source: ActorSnapshot,
        target: ActorSnapshot | None,
        move: CombatMoveDTO,
    ) -> None:
        """
        Post-Calc этап: Очистка временных мутаций, применение эффектов.
        """
        if not ctx.result:
            return

        # 1. [CLEANUP TEMP ABILITIES & COLLECT EFFECTS]
        self._process_temp_abilities_post_calc(ctx, source, target)

        # 2. [EXECUTE EFFECTS]
        self._apply_queued_effects(ctx, source, target)

    # ==============================================================================
    # ATOMIC STEPS: STATUS EFFECTS (FLAGS & MODS)
    # ==============================================================================

    @staticmethod
    def _apply_status_effects(ctx: PipelineContextDTO, actor: ActorSnapshot, mode: Literal["source", "target"]) -> None:
        """
        Применяет влияние активных эффектов на контекст.
        """
        for effect in actor.statuses.effects:
            if effect.control:
                behavior = effect.control.source_behavior if mode == "source" else effect.control.target_behavior
                if behavior:
                    if mode == "source" and behavior.get("can_act") is False:
                        ctx.phases.run_calculator = False
                        ctx.result.skip_reason = "CONTROLLED"

                    for path, value in behavior.items():
                        if path == "can_act":
                            continue
                        AbilityService._set_nested_flag(ctx, path, value)
            pass

    @staticmethod
    def _set_nested_flag(root_obj: Any, path: str, value: Any) -> None:
        parts = path.split(".")
        obj = root_obj
        try:
            for part in parts[:-1]:
                obj = getattr(obj, part)
            setattr(obj, parts[-1], value)
        except AttributeError:
            log.warning(f"AbilityService | Invalid flag path: {path}")

    # ==============================================================================
    # UNIVERSAL LOGIC HANDLER (PRE-CALC)
    # ==============================================================================

    @staticmethod
    def _extract_action_id(move: CombatMoveDTO, mode: Literal["ability", "feint"]) -> str | None:
        """
        Безопасное извлечение ID действия из payload с проверкой типов.
        """
        payload = move.payload

        # 1. Fallback для словарей (если Pydantic не сработал или legacy)
        if isinstance(payload, dict):
            if mode == "ability":
                return payload.get("ability_id")
            if mode == "feint":
                return payload.get("feint_id")
            return None

        # 2. Строгая проверка DTO
        if mode == "ability":
            # Ability ID есть только в InstantPayload
            if isinstance(payload, InstantPayload):
                return payload.ability_id
            return None

        if mode == "feint":
            # Feint ID есть и в ExchangePayload, и в InstantPayload
            if isinstance(payload, (ExchangePayload, InstantPayload)):
                return payload.feint_id
            return None

        return None

    @staticmethod
    def _process_action_logic(
        ctx: PipelineContextDTO,
        move: CombatMoveDTO,
        actor: ActorSnapshot,
        target: ActorSnapshot | None,
        mode: Literal["ability", "feint"],
    ) -> None:
        """
        Универсальная логика обработки действия (Абилка или Финт).
        """
        config: AbilityConfigDTO | FeintConfigDTO | None = None
        cost_ok = False
        action_id: str | None = None

        if mode == "ability":
            action_id = AbilityService._extract_action_id(move, mode="ability")
            if not action_id:
                return

            config = GameData.get_ability(action_id)
            if config:
                cost_ok = AbilityService._check_ability_cost(actor, config.cost)
                if cost_ok:
                    AbilityService._register_ability_cost(ctx, config.cost)
                else:
                    ctx.phases.run_calculator = False
                    ctx.result.skip_reason = "NO_RESOURCE"
                    log.info(f"AbilityService | Not enough resources for ability {config.ability_id}")

        elif mode == "feint":
            action_id = AbilityService._extract_action_id(move, mode="feint")
            if not action_id:
                return

            config = GameData.get_feint(action_id)
            if config:
                # Финты уже оплачены (при получении в руку) и списаны (в TurnManager)
                cost_ok = True

        if not config or not cost_ok:
            return

        # [EVENT] CAST
        ctx.result.events.append(
            CombatEventDTO(
                type="CAST", source_id=actor.char_id, target_id=target.char_id if target else None, action_id=action_id
            )
        )

        ability_uid = str(uuid.uuid4())
        modified_keys = []

        if config.raw_mutations:
            AbilityService._apply_raw_mutations(actor, config.raw_mutations, source_key=ability_uid)
            modified_keys = list(config.raw_mutations.keys())

        payload_effects = {}
        if config.effects:
            payload_effects["is_hit"] = config.effects

        # Determine ID for ActiveAbilityDTO
        active_id = (
            config.ability_id
            if mode == "ability" and hasattr(config, "ability_id")
            else (config.feint_id if mode == "feint" and hasattr(config, "feint_id") else action_id)
        )

        active_ability = ActiveAbilityDTO(
            uid=ability_uid,
            ability_id=active_id,  # type: ignore # Pydantic validator handles this usually
            source_id=actor.char_id,
            expire_at_exchange=actor.meta.exchange_counter,
            modified_keys=modified_keys,
            payload={"effects": payload_effects},
        )
        actor.statuses.abilities.append(active_ability)

        if config.pipeline_mutations:
            if hasattr(config.pipeline_mutations, "preset") and config.pipeline_mutations.preset:
                preset_flags = PIPELINE_PRESETS.get(config.pipeline_mutations.preset, {})
                for path, value in preset_flags.items():
                    AbilityService._set_nested_flag(ctx, path, value)

            flags = getattr(config.pipeline_mutations, "flags", config.pipeline_mutations)
            if isinstance(flags, dict):
                for path, value in flags.items():
                    AbilityService._set_nested_flag(ctx, path, value)

        if config.triggers:
            for trigger in config.triggers:
                AbilityService._set_nested_flag(ctx.triggers, trigger, True)

        if config.override_damage:
            ctx.override_damage = config.override_damage

    # ==============================================================================
    # UNIVERSAL LOGIC HANDLER (POST-CALC)
    # ==============================================================================

    @staticmethod
    def _process_temp_abilities_post_calc(
        ctx: PipelineContextDTO, source: ActorSnapshot, target: ActorSnapshot | None
    ) -> None:
        """
        Шаг 1 Post-Calc: Очистка RAW и перенос эффектов из Payload в очередь applied_effects.
        """
        current_exchange = source.meta.exchange_counter
        to_remove = []

        for ability in source.statuses.abilities:
            if ability.expire_at_exchange <= current_exchange:
                for stat_key in ability.modified_keys:
                    if stat_key in source.raw.attributes:
                        if ability.uid in source.raw.attributes[stat_key]["temp"]:
                            del source.raw.attributes[stat_key]["temp"][ability.uid]
                            source.dirty_stats.add(stat_key)
                    elif stat_key in source.raw.modifiers and ability.uid in source.raw.modifiers[stat_key]["temp"]:
                        del source.raw.modifiers[stat_key]["temp"][ability.uid]
                        source.dirty_stats.add(stat_key)

                effects_map = ability.payload.get("effects", {})
                if effects_map:
                    conditions = {
                        "is_hit": ctx.result.is_hit,
                        "is_crit": ctx.result.is_crit,
                        "is_blocked": ctx.result.is_blocked,
                        "is_parried": ctx.result.is_parried,
                        "is_dodged": ctx.result.is_dodged,
                        "is_miss": ctx.result.is_miss,
                    }

                    for cond_key, effects_list in effects_map.items():
                        if conditions.get(cond_key):
                            for effect_data in effects_list:
                                AbilityService._queue_effect(ctx, effect_data, source, target)

                to_remove.append(ability)

        for ability in to_remove:
            source.statuses.abilities.remove(ability)

    @staticmethod
    def _queue_effect(
        ctx: PipelineContextDTO, effect_data: dict, source: ActorSnapshot, target: ActorSnapshot | None
    ) -> None:
        """
        Хелпер: Добавляет эффект в очередь.
        """
        if "target_id" not in effect_data:
            real_target = target if target else source
            effect_data["target_id"] = real_target.char_id

        ctx.result.applied_effects.append(effect_data)

    @staticmethod
    def _apply_queued_effects(ctx: PipelineContextDTO, source: ActorSnapshot, target: ActorSnapshot | None) -> None:
        """
        Шаг 2 Post-Calc: Физическое создание эффектов из очереди applied_effects.
        Использует EffectFactory.
        """
        for effect_data in ctx.result.applied_effects:
            target_char_id = effect_data.get("target_id")
            effect_target = source if target_char_id == source.char_id else target
            if not effect_target:
                continue

            effect_id = effect_data.get("id") or effect_data.get("effect_id")

            # 2. Instant Actions (Heal/Cleanse)
            if effect_id == "restore_hp":
                val = effect_data.get("params", {}).get("value", 0)
                if "hp" not in ctx.result.resource_changes:
                    ctx.result.resource_changes["hp"] = {}
                ctx.result.resource_changes["hp"]["heal"] = f"+{val}"

                # [EVENT] HEAL
                ctx.result.events.append(
                    CombatEventDTO(
                        type="HEAL",
                        source_id=source.char_id,
                        target_id=effect_target.char_id,
                        value=val,
                        resource="hp",
                        action_id="restore_hp",
                    )
                )
                continue

            # 3. Create Active Effect (Factory)
            if not isinstance(effect_id, str):
                continue

            config = GameData.get_effect(effect_id)
            if not config:
                continue

            params = effect_data.get("params", {})

            # ВАЖНО: Передаем damage_final как damage_ref для скалирования (например, Bleed)
            damage_ref = ctx.result.damage_final if ctx.result.damage_final > 0 else 0

            active_effect, mutations = EffectFactory.create_effect(
                config=config,
                params=params,
                source_id=source.char_id,
                current_exchange=source.meta.exchange_counter,
                damage_ref=damage_ref,  # Передаем урон
            )

            if mutations:
                AbilityService._apply_raw_mutations(effect_target, mutations, source_key=active_effect.uid)

            effect_target.statuses.effects.append(active_effect)

            # [EVENT] APPLY_EFFECT
            ctx.result.events.append(
                CombatEventDTO(
                    type="APPLY_EFFECT", source_id=source.char_id, target_id=effect_target.char_id, action_id=effect_id
                )
            )

    @staticmethod
    def _cleanup_expired_effects_pre_calc(actor: ActorSnapshot) -> None:
        """
        Удаляет эффекты, которые истекли в ПРОШЛОМ ходу.
        """
        current_exchange = actor.meta.exchange_counter
        to_remove = []

        for effect in actor.statuses.effects:
            if effect.expire_at_exchange < current_exchange:
                for stat_key in effect.modified_keys:
                    if stat_key in actor.raw.attributes:
                        if effect.uid in actor.raw.attributes[stat_key]["temp"]:
                            del actor.raw.attributes[stat_key]["temp"][effect.uid]
                            actor.dirty_stats.add(stat_key)
                    elif stat_key in actor.raw.modifiers and effect.uid in actor.raw.modifiers[stat_key]["temp"]:
                        del actor.raw.modifiers[stat_key]["temp"][effect.uid]
                        actor.dirty_stats.add(stat_key)

                to_remove.append(effect)

        for effect in to_remove:
            actor.statuses.effects.remove(effect)

    # ==============================================================================
    # HELPERS
    # ==============================================================================

    @staticmethod
    def _check_ability_cost(actor: ActorSnapshot, cost: AbilityCostDTO) -> bool:
        return (
            actor.meta.en >= cost.energy
            and actor.meta.hp >= cost.hp
            and actor.meta.tokens.get("gift", 0) >= cost.gift_tokens
        )

    @staticmethod
    def _register_ability_cost(ctx: PipelineContextDTO, cost: AbilityCostDTO) -> None:
        if cost.energy > 0:
            if "en" not in ctx.result.resource_changes:
                ctx.result.resource_changes["en"] = {}
            ctx.result.resource_changes["en"]["cost"] = f"-{cost.energy}"
        if cost.hp > 0:
            if "hp" not in ctx.result.resource_changes:
                ctx.result.resource_changes["hp"] = {}
            ctx.result.resource_changes["hp"]["cost"] = f"-{cost.hp}"
        if cost.gift_tokens > 0:
            if "gift" not in ctx.result.resource_changes:
                ctx.result.resource_changes["gift"] = {}
            ctx.result.resource_changes["gift"]["cost"] = f"-{cost.gift_tokens}"

    @staticmethod
    def _apply_raw_mutations(actor: ActorSnapshot, mutations: dict, source_key: str) -> None:
        """
        Применяет мутации к actor.raw (attributes или modifiers) и помечает dirty_stats.
        """
        for stat, value in mutations.items():
            target_dict = actor.raw.attributes if stat in actor.raw.attributes else actor.raw.modifiers

            if stat not in target_dict:
                target_dict[stat] = {"base": 0.0, "source": {}, "temp": {}}

            target_dict[stat]["temp"][source_key] = value
            actor.dirty_stats.add(stat)
