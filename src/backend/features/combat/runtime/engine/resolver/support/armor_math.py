"""Armor, resistance, and crit-multiplier math."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.combat.runtime.engine.math_core import MathCore
from src.backend.features.combat.runtime.engine.tunables import current_tunables

from . import offensive_lookup

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorStats
    from src.backend.features.combat.dto.pipeline import InteractionResultDTO, PipelineContextDTO


def effective_armor(
    atk_stats: ActorStats,
    def_stats: ActorStats,
    ctx: PipelineContextDTO,
    incoming_damage: float = 0.0,
    res: InteractionResultDTO | None = None,
) -> float:
    return effective_armor_trace(atk_stats, def_stats, ctx, incoming_damage=incoming_damage, res=res)[0]


def effective_armor_trace(
    atk_stats: ActorStats,
    def_stats: ActorStats,
    ctx: PipelineContextDTO,
    *,
    incoming_damage: float = 0.0,
    res: InteractionResultDTO | None = None,
) -> tuple[float, dict[str, Any]]:
    armor_raw = max(0.0, float(def_stats.mods.armor or 0.0))
    shield_guard_power = _shield_guard_power(def_stats, ctx, res)
    total_power = armor_raw + shield_guard_power
    armor_type = _armor_type(def_stats, ctx)
    mastery = _armor_mastery(def_stats, armor_type)
    mastery_gate = 0.35 + (0.65 * mastery)
    coef, cap = _armor_profile(armor_type)
    trace: dict[str, Any] = {
        "mode": "percent_power",
        "type": armor_type,
        "raw": armor_raw,
        "shield_guard_power": shield_guard_power,
        "total_power": total_power,
        "effective_power": 0.0,
        "mastery": mastery,
        "mastery_gate": mastery_gate,
        "coef": coef,
        "cap": cap,
        "pct_raw": 0.0,
        "pct": 0.0,
        "absorbed": 0.0,
        "effective": 0.0,
        "ignored": total_power,
        "chance": 0.0,
        "roll": None,
        "passed": False,
        "penetration_pct": 0.0,
        "penetration_flat": 0.0,
    }
    if ctx.flags.formula.ignore_armor or ctx.flags.formula.ignore_flat_armor:
        trace["passed"] = True
        trace["reason"] = "ignore_armor"
        return 0.0, trace

    armor_power = total_power
    ignore_chance = offensive_lookup.get_offensive_val(atk_stats, ctx, "armor_ignore_chance")
    if ctx.flags.formula.roll_flat_armor_ignore:
        ignore_chance += max(0.0, ctx.mods.flat_armor_ignore_chance_bonus)
    trace["chance"] = ignore_chance
    if ignore_chance > 0.0:
        roll, passed = MathCore.roll_chance(ignore_chance)
        trace["roll"] = roll
        trace["passed"] = passed
        if passed:
            return 0.0, trace

    penetration_pct = max(0.0, offensive_lookup.get_offensive_val(atk_stats, ctx, "armor_penetration_pct"))
    if ctx.flags.formula.boost_flat_armor_penetration:
        penetration_pct += max(0.0, ctx.mods.flat_armor_penetration_bonus_pct)
    penetration_flat = max(0.0, atk_stats.mods.armor_penetration_flat)
    armor_power *= max(0.0, 1.0 - penetration_pct)
    effective_power = max(0.0, armor_power - penetration_flat)
    effective_power *= mastery_gate
    pct_raw = 1.0 - (1.0 / (1.0 + (effective_power * coef))) if effective_power > 0.0 else 0.0
    pct = max(0.0, min(cap, pct_raw))
    absorbed = max(0.0, incoming_damage) * pct
    trace["effective_power"] = effective_power
    trace["pct_raw"] = pct_raw
    trace["pct"] = pct
    trace["absorbed"] = absorbed
    trace["effective"] = absorbed
    trace["ignored"] = max(0.0, total_power - max(0.0, armor_power - penetration_flat))
    trace["penetration_pct"] = penetration_pct
    trace["penetration_flat"] = penetration_flat
    return absorbed, trace


def _armor_type(def_stats: ActorStats, ctx: PipelineContextDTO) -> str:
    if ctx.flags.mastery.light_armor:
        return "light"
    if ctx.flags.mastery.medium_armor:
        return "medium"
    if getattr(def_stats.skills, "skill_heavy_armor", 0.0) > 0.0:
        return "heavy"
    if getattr(def_stats.skills, "skill_medium_armor", 0.0) > 0.0:
        return "medium"
    if getattr(def_stats.skills, "skill_light_armor", 0.0) > 0.0:
        return "light"
    return "heavy"


def _armor_mastery(def_stats: ActorStats, armor_type: str) -> float:
    skill_by_type = {
        "light": "skill_light_armor",
        "medium": "skill_medium_armor",
        "heavy": "skill_heavy_armor",
    }
    return max(0.0, min(1.0, float(getattr(def_stats.skills, skill_by_type[armor_type], 0.0) or 0.0)))


def _armor_profile(armor_type: str) -> tuple[float, float]:
    tunables = current_tunables()
    if armor_type == "light":
        return tunables.armor_light_coef, tunables.armor_light_cap
    if armor_type == "medium":
        return tunables.armor_medium_coef, tunables.armor_medium_cap
    return tunables.armor_heavy_coef, tunables.armor_heavy_cap


def _shield_guard_power(
    def_stats: ActorStats,
    ctx: PipelineContextDTO,
    res: InteractionResultDTO | None,
) -> float:
    if res is None or not res.is_blocked:
        return 0.0

    tunables = current_tunables()
    shield_mastery = max(0.0, min(1.0, float(def_stats.skills.skill_shield_mastery or 0.0)))
    mastery_gate = 0.35 + (0.65 * shield_mastery)
    shield_guard_power_base = max(0.0, float(getattr(def_stats.mods, "shield_guard_power", 0.0) or 0.0))
    endurance_power = max(0.0, float(getattr(def_stats.mods, "physical_endurance_power", 0.0) or 0.0))
    evasion = max(0.0, float(getattr(def_stats.mods, "evasion", 0.0) or 0.0))
    evasion_penalty = max(
        tunables.shield_guard_evasion_penalty_floor,
        1.0 - (evasion * tunables.shield_guard_evasion_penalty_rate),
    )
    guard = (
        (shield_guard_power_base + endurance_power) * tunables.shield_guard_absorb_rate * mastery_gate * evasion_penalty
    )
    return guard * max(0.0, ctx.mods.shield_guard_power_mult)


def effective_physical_resistance(atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO) -> float:
    if ctx.flags.formula.ignore_physical_resistance:
        return 0.0

    phys_res = max(0.0, def_stats.mods.physical_resistance)
    if ctx.flags.formula.suppress_physical_resistance:
        suppression_pct = max(0.0, ctx.mods.physical_resistance_suppression_pct)
        phys_res *= max(0.0, 1.0 - suppression_pct)

    phys_suppression = max(0.0, offensive_lookup.get_offensive_val(atk_stats, ctx, "physical_suppression"))
    return max(0.0, phys_res - phys_suppression)


def calculate_crit_multiplier(ctx: PipelineContextDTO) -> float:
    elements = ["fire", "water", "air", "earth", "light", "darkness", "arcane", "nature"]
    is_magic = any(getattr(ctx.flags.damage, elem, False) for elem in elements)
    if is_magic:
        return 3.0 * max(0.0, ctx.mods.crit_damage_mult)

    if ctx.flags.formula.crit_damage_boost:
        return ctx.mods.weapon_effect_value * max(0.0, ctx.mods.crit_damage_mult)

    return max(0.0, ctx.mods.crit_damage_mult)
