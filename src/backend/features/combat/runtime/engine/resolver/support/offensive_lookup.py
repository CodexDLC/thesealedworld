"""Source-aware offensive stat lookup, accuracy skill bonus, and accuracy-penalty math.

Constants previously hardcoded here (``BASE_ACCURACY_CHANCE``,
``SKILL_ACCURACY_BONUS_AT_FULL``) now come from
``current_tunables()`` to honor Redis-backed combat balance overrides.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.combat.runtime.engine.tunables import current_tunables

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorStats
    from src.backend.features.combat.dto.pipeline import PipelineContextDTO


def get_offensive_val(stats: ActorStats, ctx: PipelineContextDTO, key: str) -> float:
    """Resolve a per-source modifier (main_hand / off_hand / magic / item)."""
    source = ctx.flags.meta.source_type

    prefix = "main_hand"
    if source == "off_hand":
        prefix = "off_hand"
    elif source == "magic":
        prefix = "magical"
    elif source == "item":
        prefix = "item"

    if key == "damage_base":
        return {
            "off_hand": stats.mods.off_hand_damage_base,
            "magic": stats.mods.magical_damage,
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

    if key == "accuracy_penalty":
        return {
            "magic": 0.0,
            "item": stats.mods.item_accuracy_penalty,
            "off_hand": stats.mods.off_hand_accuracy_penalty,
        }.get(source, stats.mods.main_hand_accuracy_penalty)

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

    full_key = f"{prefix}_{key}"
    if hasattr(stats.mods, full_key):
        return getattr(stats.mods, full_key)

    return 0.0


def normalized_skill_value(value: Any) -> float:
    """Clamp a raw skill value to ``0..1``."""
    return max(0.0, min(1.0, float(value or 0.0)))


def weapon_skill_value(atk_stats: ActorStats, ctx: PipelineContextDTO) -> float:
    """Normalized skill for the active weapon class, or ``0.0`` if no class set."""
    weapon_class = ctx.flags.meta.weapon_class
    if not weapon_class:
        return 0.0
    return normalized_skill_value(getattr(atk_stats.skills, f"skill_{weapon_class}", 0.0))


def style_skill_value(atk_stats: ActorStats, ctx: PipelineContextDTO) -> float:
    """Normalized skill for the active tactical-style skill key (e.g., ``skill_swords``)."""
    style_skill = ctx.flags.meta.tactical_style_skill
    if not style_skill:
        return 0.0
    return normalized_skill_value(getattr(atk_stats.skills, style_skill, 0.0))


def accuracy_skill_bonus(atk_stats: ActorStats, ctx: PipelineContextDTO) -> float:
    """Bonus to base accuracy from weapon mastery (0 → ``tunables.skill_accuracy_bonus_at_full``)."""
    return weapon_skill_value(atk_stats, ctx) * current_tunables().skill_accuracy_bonus_at_full


def accuracy_penalty_after_mastery(raw_penalty: float, weapon_skill: float, style_skill: float) -> float:
    """Reduce a raw accuracy penalty by weapon/style mastery; clamped to a min multiplier.

    Mirrors the formula in the historical ``CombatResolver._accuracy_penalty_after_mastery``.
    """
    if raw_penalty <= 0.0:
        return 0.0
    tunables = current_tunables()
    reduction = (
        weapon_skill * tunables.accuracy_penalty_weapon_skill_reduction_at_full
        + style_skill * tunables.accuracy_penalty_style_skill_reduction_at_full
    )
    penalty_mult = max(tunables.accuracy_penalty_min_multiplier, 1.0 - reduction)
    return raw_penalty * penalty_mult
