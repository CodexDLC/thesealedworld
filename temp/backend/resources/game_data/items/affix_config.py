"""
КОНФИГУРАЦИЯ АФФИКСОВ И БАНДЛОВ
===============================

Этот модуль содержит:
1. EFFECTS_DB: Атомарные эффекты (кирпичики), привязанные к modifier_dto.py.
2. BUNDLES_DB: Сборные сеты эффектов (суффиксы), требующие эссенций и слотов.

Бандлы разделены по файлам в папке `affixes/` в зависимости от стоимости слотов.
"""

from typing import TypedDict, cast

from .affixes.bundles_2_slots import BUNDLES_2_SLOTS
from .affixes.bundles_3_slots import BUNDLES_3_SLOTS
from .affixes.bundles_4_slots import BUNDLES_4_SLOTS


# --- 1. АТОМАРНЫЕ ЭФФЕКТЫ (EFFECTS) ---
class EffectData(TypedDict):
    target_field: str
    base_value: float
    is_percentage: bool
    narrative_tags: list[str]


EFFECTS_DB: dict[str, EffectData] = {
    "phys_dmg_flat": {
        "target_field": "physical_damage_bonus",
        "base_value": 0.05,
        "is_percentage": True,
        "narrative_tags": ["strong", "forceful"],
    },
    "phys_penetration": {
        "target_field": "physical_penetration",
        "base_value": 0.05,
        "is_percentage": True,
        "narrative_tags": ["piercing", "sharp"],
    },
    "phys_accuracy": {
        "target_field": "physical_accuracy",
        "base_value": 0.05,
        "is_percentage": True,
        "narrative_tags": ["precise", "accurate"],
    },
    "crit_chance": {
        "target_field": "physical_crit_chance",
        "base_value": 0.03,
        "is_percentage": True,
        "narrative_tags": ["deadly", "critical"],
    },
    "crit_power": {
        "target_field": "physical_crit_power_float",
        "base_value": 0.10,
        "is_percentage": True,
        "narrative_tags": ["brutal", "devastating"],
    },
    "magic_dmg_pct": {
        "target_field": "magical_damage_bonus",
        "base_value": 0.05,
        "is_percentage": True,
        "narrative_tags": ["arcane", "mystic"],
    },
    "magic_penetration": {
        "target_field": "magical_penetration",
        "base_value": 0.05,
        "is_percentage": True,
        "narrative_tags": ["void", "piercing"],
    },
    "phys_resist": {
        "target_field": "physical_resistance",
        "base_value": 0.03,
        "is_percentage": True,
        "narrative_tags": ["hard", "sturdy"],
    },
    "magic_resist": {
        "target_field": "magical_resistance",
        "base_value": 0.03,
        "is_percentage": True,
        "narrative_tags": ["warded", "shielded"],
    },
    "dodge": {
        "target_field": "dodge_chance",
        "base_value": 0.02,
        "is_percentage": True,
        "narrative_tags": ["agile", "elusive"],
    },
    "parry": {
        "target_field": "parry_chance",
        "base_value": 0.02,
        "is_percentage": True,
        "narrative_tags": ["defensive", "guarding"],
    },
    "block_chance": {
        "target_field": "shield_block_chance",
        "base_value": 0.03,
        "is_percentage": True,
        "narrative_tags": ["blocking", "wall"],
    },
    "hp_max": {
        "target_field": "hp_max",
        "base_value": 20.0,
        "is_percentage": False,
        "narrative_tags": ["vitality", "healthy"],
    },
    "energy_max": {
        "target_field": "energy_max",
        "base_value": 10.0,
        "is_percentage": False,
        "narrative_tags": ["mind", "spirit"],
    },
    "hp_regen": {
        "target_field": "hp_regen",
        "base_value": 1.0,
        "is_percentage": False,
        "narrative_tags": ["regeneration", "troll"],
    },
    "energy_regen": {
        "target_field": "energy_regen",
        "base_value": 0.5,
        "is_percentage": False,
        "narrative_tags": ["meditation", "focus"],
    },
    "fire_dmg": {
        "target_field": "fire_damage_bonus",
        "base_value": 0.05,
        "is_percentage": True,
        "narrative_tags": ["burning", "fiery"],
    },
    "fire_res": {
        "target_field": "fire_resistance",
        "base_value": 0.10,
        "is_percentage": True,
        "narrative_tags": ["fireproof", "dousing"],
    },
    "vampirism": {
        "target_field": "vampiric_power",
        "base_value": 0.02,
        "is_percentage": True,
        "narrative_tags": ["vampiric", "blood"],
    },
    "thorns": {
        "target_field": "thorns_damage_reflect",
        "base_value": 0.05,
        "is_percentage": True,
        "narrative_tags": ["spiked", "thorny"],
    },
    "loot_chance": {
        "target_field": "find_loot_chance",
        "base_value": 0.05,
        "is_percentage": True,
        "narrative_tags": ["lucky", "fortune"],
    },
    "craft_speed": {
        "target_field": "crafting_speed",
        "base_value": 0.05,
        "is_percentage": True,
        "narrative_tags": ["artisan", "skilled"],
    },
    "env_cold_res": {
        "target_field": "environment_cold_resistance",
        "base_value": 5.0,
        "is_percentage": False,
        "narrative_tags": ["warm", "insulated"],
    },
    "env_heat_res": {
        "target_field": "environment_heat_resistance",
        "base_value": 5.0,
        "is_percentage": False,
        "narrative_tags": ["cool", "ventilated"],
    },
}


# --- 2. БАНДЛЫ (СУФФИКСЫ) ---
class BundleData(TypedDict):
    id: str
    ingredient_id: str
    cost_slots: int
    min_tier: int
    effects: list[str]
    narrative_tags: list[str]


# Сборка всех бандлов
BUNDLES_DB: dict[str, BundleData] = (
    cast(dict[str, BundleData], BUNDLES_2_SLOTS)
    | cast(dict[str, BundleData], BUNDLES_3_SLOTS)
    | cast(dict[str, BundleData], BUNDLES_4_SLOTS)
)
