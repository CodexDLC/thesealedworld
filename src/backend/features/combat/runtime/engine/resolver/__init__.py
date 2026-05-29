"""CombatResolver facade.

Public contract preserved: ``from ...engine.resolver import CombatResolver``
and ``CombatResolver.resolve_exchange(atk, def_, ctx)``. Internally the work
flows through the orchestrator and Step singletons; the private ``_step_*``
and helper methods remain on the class as deprecated delegates so the
existing direct-call tests in ``test_runtime_processors.py`` keep passing
until Phase 6 migrates them. All delegates carry a ``DEPRECATED facade``
comment and will be removed in Phase 6.

Damage decomposition (Phase 5) replaces the in-place ``_step_calculate_damage``
implementation below with a sub-pipeline under ``steps/damage/``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.combat.dto.pipeline import (
    CombatEventDTO,
    InteractionResultDTO,
)
from src.backend.features.combat.runtime.engine.math_core import MathCore

from .orchestrator import run_exchange
from .steps import (
    accuracy_step,
    block_step,
    counter_check_step,
    crit_step,
    evasion_step,
    healing_step,
    parry_step,
)
from .support import (
    armor_math,
    offensive_lookup,
    token_awarder,
    trace_writer,
    trigger_activator,
)

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorStats
    from src.backend.features.combat.dto.pipeline import (
        CombatTriggerActivationDTO,
        PipelineContextDTO,
    )

SHIELD_MASTERY_ABSORB_CAP_RATIO_AT_FULL = 0.50
SHIELD_MASTERY_REFLECT_RATIO_AT_FULL = 0.50
UNARMED_MIN_EFFICIENCY = 0.5
UNARMED_MAX_EFFICIENCY = 3.0
UNARMED_NOVICE_SPREAD = 0.5
UNARMED_MASTER_SPREAD = 0.1


class CombatResolver:
    """Stateless math engine. Computes one Attacker → Defender exchange."""

    @classmethod
    def resolve_exchange(
        cls,
        attacker_stats: ActorStats,
        defender_stats: ActorStats,
        context: PipelineContextDTO,
    ) -> InteractionResultDTO:
        result = context.result
        if result is None:
            result = InteractionResultDTO()

        if not context.phases.run_calculator:
            return result

        if result.source_id is None and context.result.source_id is not None:
            result.source_id = context.result.source_id
        if result.target_id is None and context.result.target_id is not None:
            result.target_id = context.result.target_id

        run_exchange(
            attacker_stats,
            defender_stats,
            context,
            result,
            damage_callable=cls._step_calculate_damage,
        )

        return result

    # ----- Step facades (DEPRECATED — removed in Phase 6). -----

    @staticmethod
    def _step_accuracy_roll(atk_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO) -> bool:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return accuracy_step.run(atk_stats, atk_stats, ctx, res)

    @staticmethod
    def _step_crit_roll(
        atk_stats: ActorStats, _def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO
    ) -> None:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        crit_step.run(atk_stats, _def_stats, ctx, res)

    @staticmethod
    def _step_evasion_roll(
        atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO
    ) -> bool:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return evasion_step.run(atk_stats, def_stats, ctx, res)

    @staticmethod
    def _step_parry_roll(
        atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO
    ) -> bool:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return parry_step.run(atk_stats, def_stats, ctx, res)

    @staticmethod
    def _step_block_roll(
        atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO
    ) -> bool:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return block_step.run(atk_stats, def_stats, ctx, res)

    @staticmethod
    def _step_counter_check(def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO) -> None:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        counter_check_step.run(def_stats, def_stats, ctx, res)

    @staticmethod
    def _step_calculate_healing(atk_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO) -> float:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return healing_step.run(atk_stats, atk_stats, ctx, res)

    # ----- Damage step body (decomposed into per-phase classes in Phase 5). -----

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
            base = offensive_lookup.get_offensive_val(atk_stats, ctx, "damage_base")
            spread = offensive_lookup.get_offensive_val(atk_stats, ctx, "damage_spread")

            if ctx.flags.damage.physical:
                if ctx.flags.meta.weapon_class == "unarmed":
                    unarmed = atk_stats.skills.skill_unarmed
                    efficiency = UNARMED_MIN_EFFICIENCY + ((UNARMED_MAX_EFFICIENCY - UNARMED_MIN_EFFICIENCY) * unarmed)
                    base *= efficiency
                    spread = max(UNARMED_MASTER_SPREAD, UNARMED_NOVICE_SPREAD - (0.4 * unarmed))
                base += atk_stats.mods.physical_damage_bonus

            min_d = base * (1.0 - spread)
            max_d = base * (1.0 + spread)

        raw_damage = MathCore.random_range(min_d, max_d)
        total_damage = 0.0
        damage_parts: dict[str, float] = {}
        base_before_physical = float(base or 0.0)
        physical_added = 0.0
        mitigation_pct = 0.0
        armor_flat = 0.0
        armor_trace = {
            "raw": max(0.0, getattr(def_stats.mods, "armor", 0.0)),
            "effective": 0.0,
            "ignored": 0.0,
            "chance": 0.0,
            "roll": None,
            "passed": False,
        }
        phys_res_raw = max(0.0, getattr(def_stats.mods, "physical_resistance", 0.0))
        phys_suppression = max(0.0, offensive_lookup.get_offensive_val(atk_stats, ctx, "physical_suppression"))
        phys_res_suppression_pct = (
            max(0.0, ctx.mods.physical_resistance_suppression_pct)
            if ctx.flags.formula.suppress_physical_resistance
            else 0.0
        )
        after_resist = raw_damage
        after_armor = raw_damage

        crit_multiplier = 1.0
        if res.is_crit:
            crit_multiplier = armor_math.calculate_crit_multiplier(ctx)
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

            mitigation_pct = armor_math.effective_physical_resistance(atk_stats, def_stats, ctx)
            phys_dmg *= 1.0 - mitigation_pct
            after_resist = phys_dmg

            armor_flat, armor_trace = armor_math.effective_armor_trace(atk_stats, def_stats, ctx)
            phys_dmg = max(0.0, phys_dmg - armor_flat)
            after_armor = phys_dmg
            damage_parts["physical"] = phys_dmg

            if res.is_crit:
                token_awarder.award_attacker_token(res, "crit")
            else:
                token_awarder.award_attacker_token(res, "hit")

            total_damage += phys_dmg

        if ctx.flags.damage.pure:
            pure_dmg = raw_damage
            if res.is_crit:
                pure_dmg *= 1.5
            total_damage += pure_dmg
            damage_parts["pure"] = pure_dmg

        elements = ["fire", "water", "air", "earth", "light", "darkness", "arcane", "nature"]
        elemental_damage_enabled = False
        for elem in elements:
            if getattr(ctx.flags.damage, elem, False):
                elemental_damage_enabled = True
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
        shield_absorb_cap = 0.0
        shield_guard_power = 0.0
        shield_reflect_ratio = 0.0
        shield_mastery = 0.0
        if ctx.flags.state.partial_absorb_reflect:
            shield_mastery = min(1.0, max(0.0, def_stats.skills.skill_shield_mastery))
            shield_guard_power_base = max(0.0, getattr(def_stats.mods, "shield_guard_power", 0.0))
            shield_guard_power = shield_guard_power_base * shield_mastery
            shield_absorb_cap_ratio = SHIELD_MASTERY_ABSORB_CAP_RATIO_AT_FULL * shield_mastery
            shield_absorb_cap = total_damage * shield_absorb_cap_ratio
            shield_absorb_ratio = shield_absorb_cap_ratio
            shield_reflect_ratio = (
                min(
                    max(0.0, getattr(def_stats.mods, "shield_reflect_ratio", SHIELD_MASTERY_REFLECT_RATIO_AT_FULL)),
                    SHIELD_MASTERY_REFLECT_RATIO_AT_FULL,
                )
                * shield_mastery
            )

            raw_shield_absorb = (total_damage * max(0.0, getattr(def_stats.mods, "shield_absorb_ratio", 0.40))) + (
                shield_guard_power
            )
            shield_absorb = min(total_damage, shield_absorb_cap, raw_shield_absorb)
            total_damage -= shield_absorb
            shield_reflect = shield_absorb * shield_reflect_ratio
            res.reflected_damage += int(shield_reflect)

        total_damage *= max(0.0, getattr(atk_stats.mods, "damage_mult", 1.0))
        total_damage *= ctx.mods.damage_mult
        total_damage = max(0.0, total_damage)
        damage_channel_enabled = ctx.flags.damage.physical or ctx.flags.damage.pure or elemental_damage_enabled
        if damage_channel_enabled and raw_damage > 0.0:
            total_damage = max(1.0, total_damage)
        incoming_damage_cap = max(0, int(ctx.mods.incoming_damage_cap or 0))
        if incoming_damage_cap > 0 and total_damage > 0.0:
            total_damage = min(total_damage, float(incoming_damage_cap))
        res.damage_final = int(total_damage)
        if ctx.flags.damage.physical and base is not None:
            physical_added = max(0.0, float(base) - base_before_physical)
        trace_writer.trace_damage(
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
            shield_absorb_cap=shield_absorb_cap,
            shield_absorb_ratio=shield_absorb_ratio,
            shield_guard_power=shield_guard_power,
            shield_reflect=shield_reflect,
            shield_reflect_ratio=shield_reflect_ratio,
            shield_mastery=shield_mastery,
            weapon_technique_bonus_damage=ctx.mods.weapon_technique_bonus_damage,
            phys_res=phys_res_raw,
            physical_suppression=phys_suppression,
            physical_resistance_suppression=phys_res_suppression_pct,
            effective_phys_res=mitigation_pct,
            crit_mult=crit_multiplier,
            dbp={
                "base": base_before_physical,
                "weapon": getattr(atk_stats.mods, "physical_damage", 0.0) if ctx.flags.damage.physical else 0.0,
                "bonus": getattr(atk_stats.mods, "physical_damage_bonus", 0.0) if ctx.flags.damage.physical else 0.0,
                "added": physical_added,
                "raw_roll": raw_damage,
            },
            resl={
                "raw": phys_res_raw,
                "effective": mitigation_pct,
                "suppression": phys_suppression,
                "suppression_pct": phys_res_suppression_pct,
                "after": after_resist,
            },
            arm=armor_trace,
            after_resist=after_resist,
            after_armor=after_armor,
            after_absorb=total_damage,
            incoming_damage_cap=incoming_damage_cap or None,
        )

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

    # ----- Helper facades (DEPRECATED — removed in Phase 6). -----

    @staticmethod
    def _get_offensive_val(stats: ActorStats, ctx: PipelineContextDTO, key: str) -> float:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return offensive_lookup.get_offensive_val(stats, ctx, key)

    @staticmethod
    def _accuracy_skill_bonus(atk_stats: ActorStats, ctx: PipelineContextDTO) -> float:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return offensive_lookup.accuracy_skill_bonus(atk_stats, ctx)

    @staticmethod
    def _calculate_crit_multiplier(ctx: PipelineContextDTO) -> float:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return armor_math.calculate_crit_multiplier(ctx)

    @staticmethod
    def _effective_armor(atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO) -> float:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return armor_math.effective_armor(atk_stats, def_stats, ctx)

    @staticmethod
    def _effective_armor_trace(
        atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO
    ) -> tuple[float, dict[str, Any]]:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return armor_math.effective_armor_trace(atk_stats, def_stats, ctx)

    @staticmethod
    def _effective_physical_resistance(atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO) -> float:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return armor_math.effective_physical_resistance(atk_stats, def_stats, ctx)

    @staticmethod
    def _resolve_triggers(
        ctx: PipelineContextDTO,
        res: InteractionResultDTO,
        step_key: str,
        *,
        source_stats: ActorStats | None = None,
    ) -> None:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        trigger_activator.resolve_triggers(ctx, res, step_key, source_stats=source_stats)

    @staticmethod
    def _select_trigger_activation(
        ctx: PipelineContextDTO, rule_id: str, rule_data: dict[str, Any]
    ) -> CombatTriggerActivationDTO | None:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return trigger_activator.select_trigger_activation(ctx, rule_id, rule_data)

    @staticmethod
    def _trigger_chance(rule_data: dict[str, Any], *, source_stats: ActorStats | None = None) -> float:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return trigger_activator.trigger_chance(rule_data, source_stats=source_stats)

    @staticmethod
    def _apply_trigger_effects(
        ctx: PipelineContextDTO,
        res: InteractionResultDTO,
        activation: CombatTriggerActivationDTO,
        rule_id: str,
        rule_data: dict[str, Any],
        *,
        step_key: str,
    ) -> None:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        trigger_activator.apply_trigger_effects(ctx, res, activation, rule_id, rule_data, step_key=step_key)

    @staticmethod
    def _apply_trigger_token_grants(res: InteractionResultDTO, rule_data: dict[str, Any]) -> None:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        trigger_activator.apply_trigger_token_grants(res, rule_data)

    @staticmethod
    def _award_attacker_token(res: InteractionResultDTO, token: str) -> None:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        token_awarder.award_attacker_token(res, token)

    @staticmethod
    def _award_defender_token(res: InteractionResultDTO, token: str) -> None:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        token_awarder.award_defender_token(res, token)

    @staticmethod
    def _award_token(bucket: dict[str, int], token: str) -> None:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        token_awarder.award_token(bucket, token)

    @staticmethod
    def _bonus_token_roll() -> bool:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return token_awarder.bonus_token_roll()

    @staticmethod
    def _trace_roll(
        res: InteractionResultDTO,
        stage: str,
        chance: float,
        roll: float | None,
        passed: bool,
        **details: Any,
    ) -> None:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        trace_writer.trace_roll(res, stage, chance, roll, passed, **details)

    @staticmethod
    def _trace_step(res: InteractionResultDTO, stage: str, outcome: str, **details: Any) -> None:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        trace_writer.trace_step(res, stage, outcome, **details)

    @staticmethod
    def _trace_damage(res: InteractionResultDTO, **details: Any) -> None:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        trace_writer.trace_damage(res, **details)

    @staticmethod
    def _compact_details(details: dict[str, Any]) -> str:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return trace_writer.compact_details(details)

    @staticmethod
    def _compact_trace_details(details: dict[str, Any]) -> dict[str, Any]:
        # DEPRECATED facade — removed in Phase 6 after test surface migration.
        return trace_writer.compact_trace_details(details)
