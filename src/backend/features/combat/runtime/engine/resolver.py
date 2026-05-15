import random
from typing import Any

from loguru import logger as log

from src.backend.features.combat.dto.actor import ActorStats
from src.backend.features.combat.dto.pipeline import (
    CombatCheckTraceDTO,
    CombatDamageTraceDTO,
    CombatEventDTO,
    CombatTriggerActivationDTO,
    CombatTriggerFactDTO,
    InteractionResultDTO,
    PipelineContextDTO,
)
from src.backend.features.combat.integrations import CombatCatalogIntegrator
from src.backend.features.combat.runtime.engine.math_core import MathCore
from src.backend.features.combat.runtime.engine.pipeline_mutation_service import PipelineMutationService

PARRY_SKILL_MULT_PER_POINT = 4.0
SHIELD_BLOCK_SKILL_MULT_PER_POINT = 1.5
SHIELD_MASTERY_ABSORB_RATIO_PER_POINT = 0.20
SHIELD_ABSORB_RATIO_CAP = 0.85
UNARMED_MIN_EFFICIENCY = 0.5
UNARMED_MAX_EFFICIENCY = 3.0
UNARMED_NOVICE_SPREAD = 0.5
UNARMED_MASTER_SPREAD = 0.1
TOKEN_BONUS_CHANCE = 0.30
TOKEN_BONUS_EXCLUDED = frozenset({"tempo", "gift"})


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
        Получает значение модификатора в зависимости от источника (main_hand, off_hand, magic, item).
        """
        source = ctx.flags.meta.source_type

        # Маппинг ключей
        prefix = "main_hand"  # Default is Main Hand (Physical)
        if source == "off_hand":
            prefix = "off_hand"
        elif source == "magic":
            prefix = "magical"
        elif source == "item":
            prefix = "item"

        # Спец. кейсы (явный доступ к полям DTO)
        if key == "damage_base":
            return {
                "off_hand": stats.mods.off_hand_damage_base,
                "magic": stats.mods.magical_damage,  # FIXED: magical_damage_base -> magical_damage
                "item": stats.mods.item_damage_base,
            }.get(source, stats.mods.main_hand_damage_base)

        if key == "crit_chance":
            return {
                "magic": stats.mods.magical_crit_chance,
                "item": stats.mods.item_crit_chance,
                "off_hand": stats.mods.off_hand_crit_chance + stats.mods.crit_chance,
            }.get(source, stats.mods.main_hand_crit_chance + stats.mods.crit_chance)

        if key == "accuracy":
            return {
                "magic": stats.mods.magical_accuracy + stats.mods.accuracy,
                "item": stats.mods.item_accuracy,
                "off_hand": stats.mods.off_hand_accuracy + stats.mods.accuracy,
            }.get(source, stats.mods.main_hand_accuracy + stats.mods.accuracy)

        if key == "physical_suppression":
            return {
                "magic": 0.0,
                "item": 0.0,
                "off_hand": stats.mods.physical_suppression,
            }.get(source, stats.mods.physical_suppression)

        if key == "armor_penetration_pct":
            return {
                "magic": 0.0,
                "item": stats.mods.item_armor_penetration_pct + stats.mods.armor_penetration_pct,
                "off_hand": stats.mods.off_hand_armor_penetration_pct + stats.mods.armor_penetration_pct,
            }.get(source, stats.mods.main_hand_armor_penetration_pct + stats.mods.armor_penetration_pct)

        if key == "armor_ignore_chance":
            return {
                "magic": 0.0,
                "item": stats.mods.item_armor_ignore_chance + stats.mods.armor_ignore_chance,
                "off_hand": stats.mods.off_hand_armor_ignore_chance + stats.mods.armor_ignore_chance,
            }.get(source, stats.mods.main_hand_armor_ignore_chance + stats.mods.armor_ignore_chance)

        # Fallback (если ключ не специфичен, например damage_spread)
        full_key = f"{prefix}_{key}"
        if hasattr(stats.mods, full_key):
            return getattr(stats.mods, full_key)

        return 0.0

    @staticmethod
    def _step_accuracy_roll(atk_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO) -> bool:
        if not ctx.stages.check_accuracy:
            return True

        source_id = res.source_id if res.source_id is not None else "0"
        target_id = res.target_id if res.target_id is not None else "0"

        if ctx.flags.force.miss:
            res.is_miss = True
            CombatResolver._award_defender_token(res, "tempo")
            res.events.append(CombatEventDTO(type="MISS", source_id=source_id, target_id=target_id))
            CombatResolver._trace_step(res, "accuracy", "fail", reason="force_miss")
            return False

        if ctx.flags.force.hit:
            CombatResolver._resolve_triggers(ctx, res, "ON_ACCURACY_CHECK")
            CombatResolver._trace_step(res, "accuracy", "pass", reason="force_hit")
            return True

        base_acc = CombatResolver._get_offensive_val(atk_stats, ctx, "accuracy")
        multiplier = ctx.mods.accuracy_mult
        final_acc = base_acc * multiplier
        roll, passed = MathCore.roll_chance(final_acc)
        CombatResolver._trace_roll(
            res,
            "accuracy",
            final_acc,
            roll,
            passed,
            base=base_acc,
            mult=multiplier,
            source_type=ctx.flags.meta.source_type,
        )

        if not passed:
            res.is_miss = True
            CombatResolver._award_defender_token(res, "tempo")
            res.events.append(CombatEventDTO(type="MISS", source_id=source_id, target_id=target_id))
            CombatResolver._resolve_triggers(ctx, res, "ON_MISS")
            return False

        CombatResolver._resolve_triggers(ctx, res, "ON_ACCURACY_CHECK")
        return True

    @staticmethod
    def _step_evasion_roll(
        atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO
    ) -> bool:
        if not ctx.stages.check_evasion:
            return False

        source_id = res.source_id if res.source_id is not None else "0"
        target_id = res.target_id if res.target_id is not None else "0"

        if ctx.flags.force.dodge:
            res.is_dodged = True
            CombatResolver._award_defender_token(res, "dodge")
            res.events.append(CombatEventDTO(type="DODGE", source_id=source_id, target_id=target_id))
            CombatResolver._resolve_triggers(ctx, res, "ON_DODGE")
            ctx.flags.state.check_counter = True
            return True

        if ctx.flags.force.hit_evasion:
            CombatResolver._resolve_triggers(ctx, res, "ON_DODGE_FAIL")
            return False

        base_evasion = def_stats.mods.evasion  # FIXED: dodge_chance -> evasion
        evasion_cap = def_stats.mods.dodge_cap
        anti_evasion = atk_stats.mods.anti_dodge_chance

        if ctx.flags.formula.ignore_evasion_cap:
            final_chance = base_evasion - anti_evasion
        elif ctx.flags.formula.zero_anti_evasion:
            final_chance = base_evasion
            final_chance = min(final_chance, evasion_cap)
        else:
            final_chance = base_evasion - anti_evasion
            final_chance = min(final_chance, evasion_cap)

        if final_chance <= 0:
            CombatResolver._resolve_triggers(ctx, res, "ON_DODGE_FAIL")
            CombatResolver._trace_roll(
                res,
                "evasion",
                final_chance,
                None,
                False,
                base=base_evasion,
                cap=evasion_cap,
                anti=anti_evasion,
            )
            return False

        roll, passed = MathCore.roll_chance(final_chance)
        CombatResolver._trace_roll(
            res,
            "evasion",
            final_chance,
            roll,
            passed,
            base=base_evasion,
            cap=evasion_cap,
            anti=anti_evasion,
        )

        if passed:
            res.is_dodged = True
            CombatResolver._award_defender_token(res, "dodge")
            res.events.append(CombatEventDTO(type="DODGE", source_id=source_id, target_id=target_id))
            CombatResolver._resolve_triggers(ctx, res, "ON_DODGE")
            ctx.flags.state.check_counter = True
            return True
        else:
            CombatResolver._resolve_triggers(ctx, res, "ON_DODGE_FAIL")
            return False

    @staticmethod
    def _step_parry_roll(
        atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO
    ) -> bool:
        if not ctx.stages.check_parry:
            return False

        source_id = res.source_id if res.source_id is not None else "0"
        target_id = res.target_id if res.target_id is not None else "0"

        if ctx.flags.restriction.ignore_parry:
            CombatResolver._resolve_triggers(ctx, res, "ON_PARRY_FAIL")
            return False

        if ctx.flags.force.parry:
            res.is_parried = True
            CombatResolver._award_defender_token(res, "parry")
            res.events.append(CombatEventDTO(type="PARRY", source_id=source_id, target_id=target_id))
            CombatResolver._resolve_triggers(ctx, res, "ON_PARRY")
            if (
                ctx.flags.mastery.medium_armor
                or ctx.flags.state.allow_counter_on_parry
                or ctx.flags.state.force_counter_on_parry
            ):
                ctx.flags.state.check_counter = True
            return True

        parry_base = def_stats.mods.parry  # FIXED: parry_chance -> parry
        parry_cap = def_stats.mods.parry_cap
        parrying = def_stats.skills.skill_parrying
        skill_mult = 1.0 + (PARRY_SKILL_MULT_PER_POINT * parrying)
        parry_chance = parry_base * skill_mult

        if ctx.flags.formula.ignore_parry_cap:
            final_chance = parry_chance
        else:
            final_chance = parry_chance
            final_chance = min(final_chance, parry_cap)

        roll, passed = MathCore.roll_chance(final_chance)
        CombatResolver._trace_roll(
            res,
            "parry",
            final_chance,
            roll,
            passed,
            base=parry_base,
            cap=parry_cap,
            skill=parrying,
            skill_mult=skill_mult,
        )

        if passed:
            res.is_parried = True
            CombatResolver._award_defender_token(res, "parry")
            res.events.append(CombatEventDTO(type="PARRY", source_id=source_id, target_id=target_id))
            CombatResolver._resolve_triggers(ctx, res, "ON_PARRY")

            if ctx.flags.mastery.medium_armor:
                mastery_chance = def_stats.skills.skill_medium_armor
                if MathCore.check_chance(mastery_chance):
                    ctx.flags.state.check_counter = True
            elif ctx.flags.state.allow_counter_on_parry or ctx.flags.state.force_counter_on_parry:
                ctx.flags.state.check_counter = True
            return True
        else:
            CombatResolver._resolve_triggers(ctx, res, "ON_PARRY_FAIL")
            return False

    @staticmethod
    def _step_block_roll(
        atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO
    ) -> bool:
        if not ctx.stages.check_block:
            return False

        source_id = res.source_id if res.source_id is not None else "0"
        target_id = res.target_id if res.target_id is not None else "0"

        if ctx.flags.restriction.ignore_block:
            CombatResolver._resolve_triggers(ctx, res, "ON_BLOCK_FAIL")
            return False
        if ctx.flags.force.block:
            res.is_blocked = True
            CombatResolver._award_defender_token(res, "block")
            res.events.append(CombatEventDTO(type="BLOCK", source_id=source_id, target_id=target_id))
            CombatResolver._resolve_triggers(ctx, res, "ON_BLOCK")
            return True

        block_base = def_stats.mods.block  # FIXED: shield_block_chance -> block
        block_cap = def_stats.mods.shield_block_cap
        parrying = def_stats.skills.skill_parrying
        skill_mult = 1.0 + (SHIELD_BLOCK_SKILL_MULT_PER_POINT * parrying)
        block_chance = block_base * skill_mult

        final_chance = block_chance if ctx.flags.formula.ignore_block_cap else min(block_chance, block_cap)

        roll, passed = MathCore.roll_chance(final_chance)
        CombatResolver._trace_roll(
            res,
            "block",
            final_chance,
            roll,
            passed,
            base=block_base,
            cap=block_cap,
            skill=parrying,
            skill_mult=skill_mult,
        )

        if passed:
            res.is_blocked = True
            CombatResolver._award_defender_token(res, "block")
            res.events.append(CombatEventDTO(type="BLOCK", source_id=source_id, target_id=target_id))
            CombatResolver._resolve_triggers(ctx, res, "ON_BLOCK")
            return True

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

        if res.is_dodged and ctx.flags.state.counter_to_cap_on_dodge:
            counter_chance = max(counter_chance, cap)

        if (res.is_dodged and ctx.flags.state.force_counter_on_dodge) or (
            res.is_parried and ctx.flags.state.force_counter_on_parry
        ):
            counter_chance = 1.0

        if counter_chance > 0 and MathCore.check_chance(counter_chance):
            res.is_counter = True
            CombatResolver._award_defender_token(res, "counter")
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
            skill_multiplier = 1.0 + skill_val

        final_chance = my_crit_chance * skill_multiplier
        crit_cap = CombatResolver._get_offensive_val(atk_stats, ctx, "crit_cap")
        final_chance = min(final_chance, crit_cap)

        roll, passed = MathCore.roll_chance(final_chance)
        CombatResolver._trace_roll(
            res,
            "crit",
            final_chance,
            roll,
            passed,
            base=my_crit_chance,
            cap=crit_cap,
            skill_mult=skill_multiplier,
        )

        if passed:
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

        source_id = res.source_id if res.source_id is not None else "0"
        target_id = res.target_id if res.target_id is not None else "0"

        if ctx.override_damage:
            min_d, max_d = ctx.override_damage
            base = None
            spread = None
        else:
            base = CombatResolver._get_offensive_val(atk_stats, ctx, "damage_base")
            spread = CombatResolver._get_offensive_val(atk_stats, ctx, "damage_spread")

            if ctx.flags.damage.physical:
                if ctx.flags.meta.weapon_class == "unarmed":
                    unarmed = atk_stats.skills.skill_unarmed
                    efficiency = UNARMED_MIN_EFFICIENCY + ((UNARMED_MAX_EFFICIENCY - UNARMED_MIN_EFFICIENCY) * unarmed)
                    base *= efficiency
                    spread = max(UNARMED_MASTER_SPREAD, UNARMED_NOVICE_SPREAD - (0.4 * unarmed))
                else:
                    base += atk_stats.mods.physical_damage
                base += atk_stats.mods.physical_damage_bonus

            min_d = base * (1.0 - spread)
            max_d = base * (1.0 + spread)

        raw_damage = MathCore.random_range(min_d, max_d)
        total_damage = 0.0
        damage_parts: dict[str, float] = {}

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
            phys_suppression_pct = CombatResolver._get_offensive_val(atk_stats, ctx, "physical_suppression")
            mitigation_pct = max(0.0, phys_res_pct - phys_suppression_pct)
            phys_dmg *= 1.0 - mitigation_pct

            armor_flat = CombatResolver._effective_armor(atk_stats, def_stats, ctx)
            phys_dmg = max(0.0, phys_dmg - armor_flat)
            damage_parts["physical"] = phys_dmg

            if res.is_crit:
                CombatResolver._award_attacker_token(res, "crit")
            else:
                CombatResolver._award_attacker_token(res, "hit")

            total_damage += phys_dmg

        if ctx.flags.damage.pure:
            pure_dmg = raw_damage
            if res.is_crit:
                pure_dmg *= 1.5
            total_damage += pure_dmg
            damage_parts["pure"] = pure_dmg

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
                damage_parts[elem] = elem_dmg

        if ctx.flags.state.hit_index > 0:
            heavy_skill = def_stats.skills.skill_heavy_armor
            if heavy_skill > 0:
                total_damage *= 1.0 - (heavy_skill * 0.5)

        shield_absorb = 0.0
        shield_reflect = 0.0
        shield_absorb_ratio = 0.0
        shield_guard_power = 0.0
        shield_reflect_ratio = 0.0
        if ctx.flags.state.partial_absorb_reflect:
            shield_guard_power = max(0.0, getattr(def_stats.mods, "shield_guard_power", 0.0))
            shield_absorb_ratio = max(0.0, getattr(def_stats.mods, "shield_absorb_ratio", 0.40))
            shield_absorb_ratio += (
                max(0.0, def_stats.skills.skill_shield_mastery) * SHIELD_MASTERY_ABSORB_RATIO_PER_POINT
            )
            shield_absorb_ratio = min(shield_absorb_ratio, SHIELD_ABSORB_RATIO_CAP)
            shield_reflect_ratio = max(0.0, getattr(def_stats.mods, "shield_reflect_ratio", 1.0))

            shield_absorb = min(total_damage, (total_damage * shield_absorb_ratio) + shield_guard_power)
            total_damage -= shield_absorb
            shield_reflect = shield_absorb * shield_reflect_ratio
            res.reflected_damage += int(shield_reflect)

        total_damage *= max(0.0, getattr(atk_stats.mods, "damage_mult", 1.0))
        total_damage *= ctx.mods.damage_mult
        total_damage = max(0.0, total_damage)
        res.damage_final = int(total_damage)
        CombatResolver._trace_damage(
            res,
            raw=raw_damage,
            final=total_damage,
            min_d=min_d,
            max_d=max_d,
            base=base,
            spread=spread,
            parts=damage_parts,
            armor=getattr(def_stats.mods, "armor", 0.0),
            shield_absorb=shield_absorb,
            shield_absorb_ratio=shield_absorb_ratio,
            shield_guard_power=shield_guard_power,
            shield_reflect=shield_reflect,
            shield_reflect_ratio=shield_reflect_ratio,
            weapon_technique_bonus_damage=ctx.mods.weapon_technique_bonus_damage,
            phys_res=getattr(def_stats.mods, "physical_resistance", 0.0),
            physical_suppression=CombatResolver._get_offensive_val(atk_stats, ctx, "physical_suppression"),
            crit_mult=crit_multiplier,
        )

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

        source_id = res.source_id if res.source_id is not None else "0"
        target_id = res.target_id if res.target_id is not None else "0"

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
            rule_data = CombatCatalogIntegrator.get_trigger_rule(rule_id)
            if not rule_data:
                continue

            if rule_data.get("event") != step_key:
                continue

            activation = CombatResolver._select_trigger_activation(ctx, rule_id, rule_data)
            if activation is None:
                continue

            # 4. Шанс
            raw_chance = rule_data.get("chance", 0.0)
            chance = float(raw_chance) if isinstance(raw_chance, (int, float)) else 0.0

            if not MathCore.check_chance(chance):
                continue

            res.fired_triggers.append(rule_id)
            res.trigger_facts.append(
                CombatTriggerFactDTO(
                    trigger_id=rule_id,
                    event=step_key,
                    source=activation.source,
                    source_id=activation.source_id,
                    source_slot=activation.source_slot,
                    chance=chance,
                    display_policy=str(rule_data.get("display_policy") or "merge"),
                    stacking_rule=str(rule_data.get("stacking_rule") or "unique"),
                    tags=[*activation.tags, *[str(tag) for tag in rule_data.get("tags", [])]],
                )
            )

            # 5. Pipeline-local mutations. Effects/tokens stay separate technical outputs.
            PipelineMutationService.apply(
                applications=rule_data.get("pipeline_mutations", []),
                ctx=ctx,
                source=activation.source,
            )
            CombatResolver._apply_trigger_effects(res, rule_id, rule_data, step_key=step_key)
            CombatResolver._apply_trigger_token_grants(res, rule_data)

    @staticmethod
    def _apply_trigger_effects(
        res: InteractionResultDTO,
        rule_id: str,
        rule_data: dict[str, Any],
        *,
        step_key: str,
    ) -> None:
        for effect_id in rule_data.get("applied_effect_ids", []):
            effect_data = {"id": effect_id, "source_trigger_id": rule_id}
            conditions = effect_data.setdefault("conditions", {})
            if step_key == "ON_CRIT":
                conditions.setdefault("is_hit", True)
                conditions.setdefault("is_crit", True)
            res.applied_effects.append(effect_data)

    @staticmethod
    def _apply_trigger_token_grants(
        res: InteractionResultDTO,
        rule_data: dict[str, Any],
    ) -> None:
        attacker_tokens = rule_data.get("token_grants_attacker", [])
        defender_tokens = rule_data.get("token_grants_defender", [])
        for token in attacker_tokens:
            CombatResolver._award_attacker_token(res, str(token))
        for token in defender_tokens:
            CombatResolver._award_defender_token(res, str(token))

    @staticmethod
    def _award_attacker_token(res: InteractionResultDTO, token: str) -> None:
        CombatResolver._award_token(res.tokens_awarded_attacker, token)

    @staticmethod
    def _award_defender_token(res: InteractionResultDTO, token: str) -> None:
        CombatResolver._award_token(res.tokens_awarded_defender, token)

    @staticmethod
    def _award_token(bucket: dict[str, int], token: str) -> None:
        amount = 1
        if token not in TOKEN_BONUS_EXCLUDED and CombatResolver._bonus_token_roll():
            amount = 2
        bucket[token] = bucket.get(token, 0) + amount

    @staticmethod
    def _bonus_token_roll() -> bool:
        return random.random() < TOKEN_BONUS_CHANCE  # nosec B311

    @staticmethod
    def _effective_armor(atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO) -> float:
        if ctx.flags.formula.ignore_armor:
            return 0.0

        armor = max(0.0, def_stats.mods.armor)
        ignore_chance = CombatResolver._get_offensive_val(atk_stats, ctx, "armor_ignore_chance")
        if ignore_chance > 0.0 and MathCore.check_chance(ignore_chance):
            return 0.0

        penetration_pct = max(0.0, CombatResolver._get_offensive_val(atk_stats, ctx, "armor_penetration_pct"))
        penetration_flat = max(0.0, atk_stats.mods.armor_penetration_flat)
        armor *= max(0.0, 1.0 - penetration_pct)
        return max(0.0, armor - penetration_flat)

    @staticmethod
    def _select_trigger_activation(
        ctx: PipelineContextDTO, rule_id: str, rule_data: dict[str, Any]
    ) -> CombatTriggerActivationDTO | None:
        activations = ctx.trigger_activations.get(rule_id) or [
            CombatTriggerActivationDTO(trigger_id=rule_id, source="system")
        ]
        allowed_sources = set(rule_data.get("allowed_sources") or [])
        if not allowed_sources:
            return activations[0]

        for activation in activations:
            if activation.source in allowed_sources:
                return activation
        return None

    @staticmethod
    def _trace_roll(
        res: InteractionResultDTO,
        stage: str,
        chance: float,
        roll: float | None,
        passed: bool,
        **details: Any,
    ) -> None:
        compact_details = CombatResolver._compact_trace_details(details)
        res.checks.append(
            CombatCheckTraceDTO(
                stage=stage,
                chance=chance,
                roll=roll,
                passed=passed,
                details=compact_details,
            )
        )
        log.opt(colors=True).debug(
            "<cyan>CombatRoll</cyan> | {src}->{dst} stage={stage} chance={chance:.3f} roll={roll} pass={passed} {details}",
            src=res.source_id,
            dst=res.target_id,
            stage=stage,
            chance=chance,
            roll="auto" if roll is None else f"{roll:.3f}",
            passed=passed,
            details=CombatResolver._compact_details(compact_details),
        )

    @staticmethod
    def _trace_step(res: InteractionResultDTO, stage: str, outcome: str, **details: Any) -> None:
        log.opt(colors=True).debug(
            "<cyan>CombatStep</cyan> | {src}->{dst} stage={stage} outcome={outcome} {details}",
            src=res.source_id,
            dst=res.target_id,
            stage=stage,
            outcome=outcome,
            details=CombatResolver._compact_details(details),
        )

    @staticmethod
    def _trace_damage(res: InteractionResultDTO, **details: Any) -> None:
        final = details.pop("final")
        raw = details.pop("raw")
        min_d = details.pop("min_d")
        max_d = details.pop("max_d")
        compact_details = CombatResolver._compact_trace_details(details)
        res.damage_trace = CombatDamageTraceDTO(
            raw=float(raw),
            final=float(final),
            min=float(min_d),
            max=float(max_d),
            details=compact_details,
        )
        log.opt(colors=True).debug(
            "<magenta>CombatDamage</magenta> | {src}->{dst} final={final:.2f} raw={raw:.2f} range={min_d:.2f}-{max_d:.2f} {details}",
            src=res.source_id,
            dst=res.target_id,
            final=final,
            raw=raw,
            min_d=min_d,
            max_d=max_d,
            details=CombatResolver._compact_details(compact_details),
        )

    @staticmethod
    def _compact_details(details: dict[str, Any]) -> str:
        parts = []
        for key, value in details.items():
            if value is None:
                continue
            if isinstance(value, float):
                parts.append(f"{key}={value:.3f}")
            else:
                parts.append(f"{key}={value}")
        return " ".join(parts)

    @staticmethod
    def _compact_trace_details(details: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in details.items() if value is not None}
