from typing import Any

from src.backend.domains.user_features.combat.combat_engine.logic.math_core import MathCore
from src.backend.domains.user_features.combat.dto.combat_actor_dto import ActorStats
from src.backend.domains.user_features.combat.dto.combat_pipeline_dto import (
    CombatEventDTO,
    InteractionResultDTO,
    PipelineContextDTO,
)
from src.backend.resources.game_data.triggers.definitions.rules import TRIGGER_RULES_DICT


class CombatResolver:
    """
    Stateless Math Engine.
    Отвечает за расчет одного взаимодействия (Attacker -> Defender).
    """

    @classmethod
    def resolve_exchange(
        cls, attacker_stats: ActorStats, defender_stats: ActorStats, context: PipelineContextDTO
    ) -> InteractionResultDTO:
        # Используем уже созданный результат из контекста
        result = context.result
        if result is None:
            result = InteractionResultDTO()

        if not context.phases.run_calculator:
            return result

        # Ensure source_id and target_id are set in result from context if not already
        if result.source_id is None and context.result.source_id is not None:
            result.source_id = context.result.source_id
        if result.target_id is None and context.result.target_id is not None:
            result.target_id = context.result.target_id

        # 1. Accuracy
        if not cls._step_accuracy_roll(attacker_stats, context, result):
            return result

        # 2. Crit
        cls._step_crit_roll(attacker_stats, defender_stats, context, result)

        # 3. Evasion
        if cls._step_evasion_roll(attacker_stats, defender_stats, context, result):
            cls._step_counter_check(defender_stats, context, result)
            return result

        # 4. Parry
        if cls._step_parry_roll(attacker_stats, defender_stats, context, result):
            cls._step_counter_check(defender_stats, context, result)
            return result

        # 5. Block
        if cls._step_block_roll(attacker_stats, defender_stats, context, result):
            cls._step_counter_check(defender_stats, context, result)
            return result

        # 6. Damage
        cls._step_calculate_damage(attacker_stats, defender_stats, context, result)

        # 7. Healing (NEW)
        cls._step_calculate_healing(attacker_stats, context, result)

        # 8. Control Check
        if result.is_hit:
            cls._resolve_triggers(context, result, "ON_CHECK_CONTROL")

        return result

    @staticmethod
    def _get_offensive_val(stats: ActorStats, ctx: PipelineContextDTO, key: str) -> float:
        """
        Получает значение модификатора в зависимости от источника (main_hand, off_hand, magic).
        """
        source = ctx.flags.meta.source_type

        # Маппинг ключей
        prefix = "main_hand"  # Default is Main Hand (Physical)
        if source == "off_hand":
            prefix = "off_hand"
        elif source == "magic":
            prefix = "magical"

        # Спец. кейсы (явный доступ к полям DTO)
        if key == "damage_base":
            if source == "off_hand":
                return stats.mods.off_hand_damage_base
            elif source == "magic":
                return stats.mods.magical_damage  # FIXED: magical_damage_base -> magical_damage
            return stats.mods.main_hand_damage_base

        if key == "crit_chance":
            if source == "magic":
                return stats.mods.magical_crit_chance
            if source == "off_hand":
                return stats.mods.off_hand_crit_chance
            return stats.mods.main_hand_crit_chance

        if key == "accuracy":
            if source == "magic":
                return stats.mods.magical_accuracy
            if source == "off_hand":
                return stats.mods.off_hand_accuracy
            return stats.mods.main_hand_accuracy

        if key == "penetration":
            if source == "magic":
                return stats.mods.magical_penetration
            if source == "off_hand":
                return stats.mods.off_hand_penetration
            return stats.mods.main_hand_penetration

        # Fallback (если ключ не специфичен, например damage_spread)
        full_key = f"{prefix}_{key}"
        if hasattr(stats.mods, full_key):
            return getattr(stats.mods, full_key)

        return 0.0

    @staticmethod
    def _step_accuracy_roll(atk_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO) -> bool:
        if not ctx.stages.check_accuracy:
            return True

        source_id = res.source_id if res.source_id is not None else 0
        target_id = res.target_id if res.target_id is not None else 0

        if ctx.flags.force.miss:
            res.is_miss = True
            res.tokens_awarded_defender["tempo"] = 1
            res.events.append(CombatEventDTO(type="MISS", source_id=source_id, target_id=target_id))
            return False

        if ctx.flags.force.hit:
            CombatResolver._resolve_triggers(ctx, res, "ON_ACCURACY_CHECK")
            return True

        base_acc = CombatResolver._get_offensive_val(atk_stats, ctx, "accuracy")
        multiplier = ctx.mods.accuracy_mult
        final_acc = base_acc * multiplier

        if not MathCore.check_chance(final_acc):
            res.is_miss = True
            res.tokens_awarded_defender["tempo"] = 1
            res.events.append(CombatEventDTO(type="MISS", source_id=source_id, target_id=target_id))
            CombatResolver._resolve_triggers(ctx, res, "ON_MISS")
            return False

        CombatResolver._resolve_triggers(ctx, res, "ON_ACCURACY_CHECK")
        return True

    @staticmethod
    def _step_evasion_roll(
        _atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO
    ) -> bool:
        if not ctx.stages.check_evasion:
            return False

        source_id = res.source_id if res.source_id is not None else 0
        target_id = res.target_id if res.target_id is not None else 0

        if ctx.flags.force.dodge:
            res.is_dodged = True
            res.tokens_awarded_defender["dodge"] = 1
            res.events.append(CombatEventDTO(type="DODGE", source_id=source_id, target_id=target_id))
            CombatResolver._resolve_triggers(ctx, res, "ON_DODGE")
            ctx.flags.state.check_counter = True
            return True

        if ctx.flags.force.hit_evasion:
            CombatResolver._resolve_triggers(ctx, res, "ON_DODGE_FAIL")
            return False

        base_evasion = def_stats.mods.evasion  # FIXED: dodge_chance -> evasion
        evasion_cap = def_stats.mods.dodge_cap
        anti_evasion = def_stats.mods.anti_dodge_chance

        if ctx.flags.formula.evasion_halved:
            final_chance = (base_evasion * 0.5) - anti_evasion
            final_chance = min(final_chance, evasion_cap)
        elif ctx.flags.formula.ignore_evasion_cap:
            final_chance = base_evasion - anti_evasion
        elif ctx.flags.formula.zero_anti_evasion:
            final_chance = base_evasion
            final_chance = min(final_chance, evasion_cap)
        else:
            final_chance = base_evasion - anti_evasion
            final_chance = min(final_chance, evasion_cap)

        if final_chance <= 0:
            CombatResolver._resolve_triggers(ctx, res, "ON_DODGE_FAIL")
            return False

        if MathCore.check_chance(final_chance):
            res.is_dodged = True
            res.tokens_awarded_defender["dodge"] = 1
            res.events.append(CombatEventDTO(type="DODGE", source_id=source_id, target_id=target_id))
            CombatResolver._resolve_triggers(ctx, res, "ON_DODGE")
            ctx.flags.state.check_counter = True
            return True
        else:
            CombatResolver._resolve_triggers(ctx, res, "ON_DODGE_FAIL")
            return False

    @staticmethod
    def _step_parry_roll(
        _atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO
    ) -> bool:
        if not ctx.stages.check_parry:
            return False

        source_id = res.source_id if res.source_id is not None else 0
        target_id = res.target_id if res.target_id is not None else 0

        if ctx.flags.restriction.ignore_parry:
            CombatResolver._resolve_triggers(ctx, res, "ON_PARRY_FAIL")
            return False

        if ctx.flags.force.parry:
            res.is_parried = True
            res.tokens_awarded_defender["parry"] = 1
            res.events.append(CombatEventDTO(type="PARRY", source_id=source_id, target_id=target_id))
            CombatResolver._resolve_triggers(ctx, res, "ON_PARRY")
            if ctx.flags.mastery.medium_armor or ctx.flags.state.allow_counter_on_parry:
                ctx.flags.state.check_counter = True
            return True

        parry_chance = def_stats.mods.parry  # FIXED: parry_chance -> parry
        parry_cap = def_stats.mods.parry_cap

        if ctx.flags.formula.parry_halved:
            final_chance = parry_chance * 0.5
            final_chance = min(final_chance, parry_cap)
        elif ctx.flags.formula.ignore_parry_cap:
            final_chance = parry_chance
        else:
            final_chance = parry_chance
            final_chance = min(final_chance, parry_cap)

        if final_chance > 0 and MathCore.check_chance(final_chance):
            res.is_parried = True
            res.tokens_awarded_defender["parry"] = 1
            res.events.append(CombatEventDTO(type="PARRY", source_id=source_id, target_id=target_id))
            CombatResolver._resolve_triggers(ctx, res, "ON_PARRY")

            if ctx.flags.mastery.medium_armor:
                mastery_chance = def_stats.skills.skill_medium_armor
                if MathCore.check_chance(mastery_chance):
                    ctx.flags.state.check_counter = True
            elif ctx.flags.state.allow_counter_on_parry:
                ctx.flags.state.check_counter = True
            return True
        else:
            CombatResolver._resolve_triggers(ctx, res, "ON_PARRY_FAIL")
            return False

    @staticmethod
    def _step_block_roll(
        _atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO
    ) -> bool:
        if not ctx.stages.check_block:
            return False

        source_id = res.source_id if res.source_id is not None else 0
        target_id = res.target_id if res.target_id is not None else 0

        if ctx.flags.restriction.ignore_block:
            CombatResolver._resolve_triggers(ctx, res, "ON_BLOCK_FAIL")
            return False
        if ctx.flags.force.block:
            res.is_blocked = True
            res.tokens_awarded_defender["block"] = 1
            res.events.append(CombatEventDTO(type="BLOCK", source_id=source_id, target_id=target_id))
            CombatResolver._resolve_triggers(ctx, res, "ON_BLOCK")
            return True

        block_chance = def_stats.mods.block  # FIXED: shield_block_chance -> block
        block_cap = def_stats.mods.shield_block_cap

        if ctx.flags.formula.block_halved:
            final_chance = block_chance * 0.5
            final_chance = min(final_chance, block_cap)
        elif ctx.flags.formula.ignore_block_cap:
            final_chance = block_chance
        else:
            final_chance = min(block_chance, block_cap)

        if final_chance > 0 and MathCore.check_chance(final_chance):
            res.is_blocked = True
            res.tokens_awarded_defender["block"] = 1
            res.events.append(CombatEventDTO(type="BLOCK", source_id=source_id, target_id=target_id))
            CombatResolver._resolve_triggers(ctx, res, "ON_BLOCK")
            return True

        if ctx.flags.mastery.shield_reflect and MathCore.check_chance(0.25):
            ctx.flags.state.partial_absorb_reflect = True

        CombatResolver._resolve_triggers(ctx, res, "ON_BLOCK_FAIL")
        return False

    @staticmethod
    def _step_counter_check(def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO):
        if not ctx.stages.check_counter or not ctx.flags.state.check_counter:
            return

        base_chance = def_stats.mods.counter_attack_chance
        cap = def_stats.mods.counter_attack_cap
        counter_chance = min(base_chance, cap)

        if res.is_dodged and ctx.flags.mastery.light_armor and MathCore.check_chance(0.50):
            skill_lvl = def_stats.skills.skill_light_armor
            mult = 1.0 + skill_lvl
            counter_chance *= mult

        if ctx.flags.formula.counter_chance_boost:
            counter_chance += 0.20

        if counter_chance > 0 and MathCore.check_chance(counter_chance):
            res.is_counter = True
            res.tokens_awarded_defender["counter"] = 1
            res.chain_events.trigger_counter_attack = True

    @staticmethod
    def _step_crit_roll(
        atk_stats: ActorStats, _def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO
    ):
        if not ctx.stages.check_crit:
            return

        if ctx.flags.force.crit:
            res.is_crit = True
            CombatResolver._resolve_triggers(ctx, res, "ON_CRIT")
            return

        if ctx.flags.restriction.cannot_crit:
            CombatResolver._resolve_triggers(ctx, res, "ON_CRIT_FAIL")
            return

        is_magic = False
        elements = ["fire", "water", "air", "earth", "light", "darkness", "arcane", "nature"]
        for elem in elements:
            if getattr(ctx.flags.damage, elem, False):
                is_magic = True
                break

        if is_magic:
            my_crit_chance = atk_stats.mods.magical_crit_chance
        else:
            my_crit_chance = CombatResolver._get_offensive_val(atk_stats, ctx, "crit_chance")

        skill_multiplier = 1.0
        if ctx.flags.meta.weapon_class:
            skill_key = f"skill_{ctx.flags.meta.weapon_class}"
            skill_val = getattr(atk_stats.skills, skill_key, 0.0)
            skill_multiplier = 1.0 + (skill_val / 100.0)

        final_chance = my_crit_chance * skill_multiplier
        crit_cap = CombatResolver._get_offensive_val(atk_stats, ctx, "crit_cap")
        final_chance = min(final_chance, crit_cap)

        if final_chance > 0 and MathCore.check_chance(final_chance):
            res.is_crit = True
            CombatResolver._resolve_triggers(ctx, res, "ON_CRIT")
        else:
            CombatResolver._resolve_triggers(ctx, res, "ON_CRIT_FAIL")

    @staticmethod
    def _calculate_crit_multiplier(ctx: PipelineContextDTO) -> float:
        elements = ["fire", "water", "air", "earth", "light", "darkness", "arcane", "nature"]
        is_magic = any(getattr(ctx.flags.damage, elem, False) for elem in elements)
        if is_magic:
            return 3.0

        if ctx.flags.formula.crit_damage_boost:
            return ctx.mods.weapon_effect_value

        return 1.0

    @staticmethod
    def _step_calculate_damage(
        atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO
    ) -> float:
        if not ctx.stages.calculate_damage:
            return 0.0

        source_id = res.source_id if res.source_id is not None else 0
        target_id = res.target_id if res.target_id is not None else 0

        if ctx.override_damage:
            min_d, max_d = ctx.override_damage
        else:
            base = CombatResolver._get_offensive_val(atk_stats, ctx, "damage_base")
            spread = CombatResolver._get_offensive_val(atk_stats, ctx, "damage_spread")

            if ctx.flags.damage.physical:
                base += atk_stats.mods.physical_damage_bonus

            min_d = base * (1.0 - spread)
            max_d = base * (1.0 + spread)

        raw_damage = MathCore.random_range(min_d, max_d)
        total_damage = 0.0

        crit_multiplier = 1.0
        if res.is_crit:
            crit_multiplier = CombatResolver._calculate_crit_multiplier(ctx)
            res.crit_mult = crit_multiplier

        if ctx.flags.damage.physical:
            phys_dmg = raw_damage

            if res.is_crit:
                phys_dmg *= crit_multiplier
                heavy_skill = def_stats.skills.skill_heavy_armor
                if heavy_skill > 0:
                    bonus_part = crit_multiplier - 1.0
                    if bonus_part > 0:
                        phys_dmg *= 1.0 - (heavy_skill * 0.2)

            phys_res_pct = def_stats.mods.physical_resistance
            phys_pen_pct = CombatResolver._get_offensive_val(atk_stats, ctx, "penetration")
            mitigation_pct = max(0.0, phys_res_pct - phys_pen_pct)
            phys_dmg *= 1.0 - mitigation_pct

            armor_flat = def_stats.mods.armor  # FIXED: damage_reduction_flat -> armor
            phys_dmg = max(0.0, phys_dmg - armor_flat)

            if res.is_crit:
                res.tokens_awarded_attacker["crit"] = 1
            else:
                res.tokens_awarded_attacker["hit"] = 1

            total_damage += phys_dmg

        if ctx.flags.damage.pure:
            pure_dmg = raw_damage
            if res.is_crit:
                pure_dmg *= 1.5
            total_damage += pure_dmg

        elements = ["fire", "water", "air", "earth", "light", "darkness", "arcane", "nature"]
        for elem in elements:
            if getattr(ctx.flags.damage, elem, False):
                elem_dmg = raw_damage

                if res.is_crit:
                    elem_dmg *= crit_multiplier

                resist_pct = getattr(def_stats.mods, f"{elem}_resistance", 0.0)
                pen_pct = 0.0

                if atk_stats.mods.magical_penetration > 0:
                    pen_pct = atk_stats.mods.magical_penetration

                mitigation_pct = max(0.0, resist_pct - pen_pct)
                elem_dmg *= 1.0 - mitigation_pct
                total_damage += elem_dmg

        if ctx.flags.state.hit_index > 0:
            heavy_skill = def_stats.skills.skill_heavy_armor
            if heavy_skill > 0:
                total_damage *= 1.0 - (heavy_skill * 0.5)

        if ctx.flags.state.partial_absorb_reflect:
            absorbed = total_damage * 0.40
            total_damage -= absorbed
            res.reflected_damage += int(absorbed)

        total_damage = max(0.0, total_damage)
        res.damage_final = int(total_damage)

        # [EVENT] HIT
        res.is_hit = True
        tags = []
        if res.is_crit:
            tags.append("CRIT")

        res.events.append(
            CombatEventDTO(
                type="HIT",
                source_id=source_id,
                target_id=target_id,
                value=res.damage_final,
                resource="hp",
                tags=tags,
            )
        )

        return total_damage

    @staticmethod
    def _step_calculate_healing(atk_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO) -> float:
        """
        Расчет лечения (Healing).
        Использует магические статы или override_damage.
        """
        if not ctx.stages.calculate_healing:
            return 0.0

        source_id = res.source_id if res.source_id is not None else 0
        target_id = res.target_id if res.target_id is not None else 0

        # 1. Базовое значение
        if ctx.override_damage:
            min_h, max_h = ctx.override_damage
        else:
            # Если нет override, берем магическую базу (или 0)
            # TODO: Можно добавить healing_base в статы
            base = atk_stats.mods.magical_damage  # FIXED: magical_damage_base -> magical_damage
            min_h = base * 0.9
            max_h = base * 1.1

        raw_healing = MathCore.random_range(min_h, max_h)

        # 2. Крит
        if res.is_crit:
            raw_healing *= 1.5  # Стандартный крит хила
            res.crit_mult = 1.5

        # 3. Бонусы (Anatomy / Healing Power)
        # Пока используем intelligence как бонус
        # TODO: Добавить healing_power_mult в статы

        final_healing = int(raw_healing)
        res.healing_final = final_healing

        # Записываем в resource_changes (чтобы MechanicsService применил)
        if "hp" not in res.resource_changes:
            res.resource_changes["hp"] = {}

        # Используем ключ "heal" для WaterfallCalculator
        res.resource_changes["hp"]["heal"] = f"+{final_healing}"

        # [EVENT] HEAL
        tags = []
        if res.is_crit:
            tags.append("CRIT")

        res.events.append(
            CombatEventDTO(
                type="HEAL",
                source_id=source_id,
                target_id=target_id,
                value=final_healing,
                resource="hp",
                tags=tags,
            )
        )

        return float(final_healing)

    @staticmethod
    def _resolve_triggers(ctx: PipelineContextDTO, res: InteractionResultDTO, step_key: str):
        """
        Обрабатывает триггеры, используя глобальную библиотеку правил.
        Использует вложенный поиск по TriggerRulesFlagsDTO.
        """
        # 1. Определяем секцию DTO
        dto_section: Any = None
        if step_key == "ON_ACCURACY_CHECK" or step_key == "ON_MISS":
            dto_section = ctx.triggers.accuracy
        elif step_key == "ON_CRIT" or step_key == "ON_CRIT_FAIL":
            dto_section = ctx.triggers.crit
        elif step_key == "ON_DODGE" or step_key == "ON_DODGE_FAIL":
            dto_section = ctx.triggers.dodge
        elif step_key == "ON_PARRY" or step_key == "ON_PARRY_FAIL":
            dto_section = ctx.triggers.parry
        elif step_key == "ON_BLOCK" or step_key == "ON_BLOCK_FAIL":
            dto_section = ctx.triggers.block
        elif step_key == "ON_CHECK_CONTROL":
            dto_section = ctx.triggers.control
        elif step_key == "ON_DAMAGE":
            dto_section = ctx.triggers.damage

        if not dto_section:
            return

        # 2. Находим активные флаги (True)
        active_rule_ids = [k for k, v in dto_section.model_dump().items() if v is True]

        if not active_rule_ids:
            return

        # 3. Ищем правила
        for rule_id in active_rule_ids:
            rule_data = TRIGGER_RULES_DICT.get(rule_id)
            if not rule_data:
                continue

            if rule_data.get("event") != step_key:
                continue

            # 4. Шанс
            raw_chance = rule_data.get("chance", 0.0)
            chance = float(raw_chance) if isinstance(raw_chance, (int, float)) else 0.0

            if not MathCore.check_chance(chance):
                continue

            # 5. Мутации (с поддержкой точек и add_effect)
            for key, value in rule_data.get("mutations", {}).items():
                CombatResolver._apply_mutation(ctx, res, key, value)

    @staticmethod
    def _apply_mutation(ctx: PipelineContextDTO, res: InteractionResultDTO, key: str, value: Any):
        """
        Применяет мутацию к контексту или результату.
        Поддерживает вложенные ключи и спец. команду add_effect.
        """
        # 0. Спец. команда: add_effect
        if key == "add_effect" and isinstance(value, dict):
            res.applied_effects.append(value)
            return

        # 1. Разбор пути
        if "." in key:
            parts = key.split(".")
            root_name = parts[0]
            field_name = parts[1]

            # A) Flags (ctx.flags.force, ctx.flags.formula...)
            if hasattr(ctx.flags, root_name):
                sub_obj = getattr(ctx.flags, root_name)
                if hasattr(sub_obj, field_name):
                    setattr(sub_obj, field_name, value)
                    return

            # B) Chain Events (res.chain_events)
            if root_name == "chain_events" and hasattr(res.chain_events, field_name):
                setattr(res.chain_events, field_name, value)
                return

            return

        # 2. Плоский поиск (Legacy / Shortcuts)
        if hasattr(ctx.stages, key):
            setattr(ctx.stages, key, value)
        elif hasattr(ctx.flags, key):
            setattr(ctx.flags, key, value)
        elif hasattr(ctx.mods, key):
            setattr(ctx.mods, key, value)
