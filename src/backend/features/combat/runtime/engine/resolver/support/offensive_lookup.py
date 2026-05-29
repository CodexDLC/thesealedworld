"""Source-aware offensive stat lookup and accuracy skill bonus."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorStats
    from src.backend.features.combat.dto.pipeline import PipelineContextDTO

BASE_ACCURACY_CHANCE = 0.70
SKILL_ACCURACY_BONUS_AT_FULL = 0.30


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


def accuracy_skill_bonus(atk_stats: ActorStats, ctx: PipelineContextDTO) -> float:
    weapon_class = ctx.flags.meta.weapon_class
    if not weapon_class:
        return 0.0
    skill_val = getattr(atk_stats.skills, f"skill_{weapon_class}", 0.0)
    normalized = max(0.0, min(1.0, float(skill_val or 0.0)))
    return normalized * SKILL_ACCURACY_BONUS_AT_FULL
