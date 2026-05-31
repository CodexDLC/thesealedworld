"""Armor, resistance, crit-multiplier math, and shield block-branch roll."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.combat.runtime.engine.math_core import MathCore

from . import offensive_lookup, trace_writer

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorStats
    from src.backend.features.combat.dto.pipeline import InteractionResultDTO, PipelineContextDTO


def effective_armor(atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO) -> float:
    return effective_armor_trace(atk_stats, def_stats, ctx)[0]


def effective_armor_trace(
    atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO
) -> tuple[float, dict[str, Any]]:
    armor_raw = max(0.0, def_stats.mods.armor)
    trace: dict[str, Any] = {
        "raw": armor_raw,
        "effective": 0.0,
        "ignored": armor_raw,
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

    armor = armor_raw
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
    armor *= max(0.0, 1.0 - penetration_pct)
    effective = max(0.0, armor - penetration_flat)
    trace["effective"] = effective
    trace["ignored"] = max(0.0, armor_raw - effective)
    trace["penetration_pct"] = penetration_pct
    trace["penetration_flat"] = penetration_flat
    return effective, trace


def effective_physical_resistance(atk_stats: ActorStats, def_stats: ActorStats, ctx: PipelineContextDTO) -> float:
    if ctx.flags.formula.ignore_physical_resistance:
        return 0.0

    phys_res = max(0.0, def_stats.mods.physical_resistance)
    if ctx.flags.formula.suppress_physical_resistance:
        suppression_pct = max(0.0, ctx.mods.physical_resistance_suppression_pct)
        phys_res *= max(0.0, 1.0 - suppression_pct)

    phys_suppression = max(0.0, offensive_lookup.get_offensive_val(atk_stats, ctx, "physical_suppression"))
    return max(0.0, phys_res - phys_suppression)


def roll_shield_block_branch(def_stats: ActorStats, ctx: PipelineContextDTO, res: InteractionResultDTO) -> str:
    """Roll which branch a successful shield block takes: ``"defense"`` or ``"counter"``.

    Mirrors the formula in the historical ``CombatResolver._roll_shield_block_branch``.
    """
    if ctx.flags.formula.force_shield_counter_branch:
        trace_writer.trace_roll(res, "shield_block_branch", 1.0, None, True, forced="counter", branch="counter")
        return "counter"

    if ctx.flags.formula.force_shield_defense_branch:
        trace_writer.trace_roll(res, "shield_block_branch", 1.0, None, True, forced="defense", branch="defense")
        return "defense"

    defense_weight = max(0.0, float(getattr(def_stats.mods, "shield_block_defense_weight", 1.0) or 0.0))
    counter_weight = max(0.0, float(getattr(def_stats.mods, "shield_block_counter_weight", 0.0) or 0.0))
    inverted = bool(ctx.flags.formula.shield_branch_invert)
    if inverted:
        defense_weight, counter_weight = counter_weight, defense_weight
    total_weight = defense_weight + counter_weight
    defense_chance = 1.0 if total_weight <= 0.0 else defense_weight / total_weight

    roll, defense_passed = MathCore.roll_chance(defense_chance)
    branch = "defense" if defense_passed else "counter"
    trace_writer.trace_roll(
        res,
        "shield_block_branch",
        defense_chance,
        roll,
        defense_passed,
        defense_weight=defense_weight,
        counter_weight=counter_weight,
        inverted=inverted,
        branch=branch,
    )
    return branch


def calculate_crit_multiplier(ctx: PipelineContextDTO) -> float:
    elements = ["fire", "water", "air", "earth", "light", "darkness", "arcane", "nature"]
    is_magic = any(getattr(ctx.flags.damage, elem, False) for elem in elements)
    if is_magic:
        return 3.0

    if ctx.flags.formula.crit_damage_boost:
        return ctx.mods.weapon_effect_value

    return 1.0
