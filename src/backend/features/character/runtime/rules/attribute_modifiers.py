from __future__ import annotations

from src.backend.features.character.runtime.rules.vital_constants import (
    CONCENTRATION_PER_SENSOR_ATTRIBUTE,
    CONCENTRATION_REGEN_BASE,
    CONCENTRATION_REGEN_PER_SENSOR_ATTRIBUTE,
    ENERGY_PER_CORE_ATTRIBUTE,
    ENERGY_REGEN_PER_CORE_ATTRIBUTE,
    HP_PER_BODY_ATTRIBUTE,
    HP_REGEN_PER_BODY_ATTRIBUTE,
)
from src.shared.enums.stats_enums import StatKey

# Attribute -> combat modifier bridge used when a combat actor snapshot is calculated.
# AC stores plain attribute values; combat raw keeps them as {base, source, temp}.
ATTRIBUTE_MODIFIER_RULES: dict[str, dict[str, float]] = {
    # Body node
    StatKey.PHYSICAL_DAMAGE: {StatKey.STRENGTH: 1.0},
    StatKey.PHYSICAL_SUPPRESSION: {StatKey.STRENGTH: 0.02},
    StatKey.BLEED_RESISTANCE: {StatKey.ENDURANCE: 0.02},
    StatKey.ENVIRONMENT_BIO_RESISTANCE: {StatKey.ENDURANCE: 0.02},
    StatKey.EVASION: {StatKey.AGILITY: 0.05},
    StatKey.HP: {
        StatKey.STRENGTH: HP_PER_BODY_ATTRIBUTE,
        StatKey.AGILITY: HP_PER_BODY_ATTRIBUTE,
        StatKey.ENDURANCE: HP_PER_BODY_ATTRIBUTE,
    },
    StatKey.HP_REGEN: {
        StatKey.STRENGTH: HP_REGEN_PER_BODY_ATTRIBUTE,
        StatKey.AGILITY: HP_REGEN_PER_BODY_ATTRIBUTE,
        StatKey.ENDURANCE: HP_REGEN_PER_BODY_ATTRIBUTE,
    },
    StatKey.PHYSICAL_RESISTANCE: {StatKey.ENDURANCE: 0.02},
    StatKey.POISON_RESISTANCE: {StatKey.ENDURANCE: 0.02},
    # Core node
    StatKey.COUNTER_ATTACK_CHANCE: {StatKey.MEMORY: 0.0025, StatKey.PREDICTION: 0.0015},
    StatKey.EN: {
        StatKey.INTELLECT: ENERGY_PER_CORE_ATTRIBUTE,
        StatKey.MEMORY: ENERGY_PER_CORE_ATTRIBUTE,
        StatKey.MENTAL: ENERGY_PER_CORE_ATTRIBUTE,
    },
    StatKey.EN_REGEN: {
        StatKey.INTELLECT: ENERGY_REGEN_PER_CORE_ATTRIBUTE,
        StatKey.MEMORY: ENERGY_REGEN_PER_CORE_ATTRIBUTE,
        StatKey.MENTAL: ENERGY_REGEN_PER_CORE_ATTRIBUTE,
    },
    StatKey.MAGICAL_DAMAGE: {StatKey.INTELLECT: 1.0},
    StatKey.MAGICAL_PENETRATION: {StatKey.INTELLECT: 0.02},
    StatKey.MAGIC_RESIST: {StatKey.MENTAL: 0.02},
    StatKey.CONTROL_RESISTANCE: {StatKey.MENTAL: 0.02},
    StatKey.MENTAL_RESISTANCE: {StatKey.MENTAL: 0.02},
    StatKey.FIRE_RESISTANCE: {StatKey.MENTAL: 0.02},
    StatKey.WATER_RESISTANCE: {StatKey.MENTAL: 0.02},
    StatKey.AIR_RESISTANCE: {StatKey.MENTAL: 0.02},
    StatKey.EARTH_RESISTANCE: {StatKey.MENTAL: 0.02},
    StatKey.LIGHT_RESISTANCE: {StatKey.MENTAL: 0.02},
    StatKey.DARK_RESISTANCE: {StatKey.MENTAL: 0.02},
    StatKey.ARCANE_RESISTANCE: {StatKey.MENTAL: 0.02},
    StatKey.NATURE_RESISTANCE: {StatKey.MENTAL: 0.02},
    StatKey.STAMINA: {
        StatKey.PERCEPTION: CONCENTRATION_PER_SENSOR_ATTRIBUTE,
        StatKey.PROJECTION: CONCENTRATION_PER_SENSOR_ATTRIBUTE,
        StatKey.PREDICTION: CONCENTRATION_PER_SENSOR_ATTRIBUTE,
    },
    StatKey.STAMINA_REGEN: {
        StatKey.PERCEPTION: CONCENTRATION_REGEN_PER_SENSOR_ATTRIBUTE,
        StatKey.PROJECTION: CONCENTRATION_REGEN_PER_SENSOR_ATTRIBUTE,
        StatKey.PREDICTION: CONCENTRATION_REGEN_PER_SENSOR_ATTRIBUTE,
    },
    # Sensor node
    StatKey.ANTI_DODGE_CHANCE: {StatKey.PERCEPTION: 0.03},
    StatKey.INITIATIVE: {StatKey.AGILITY: 0.5},
}

DEFAULT_MODIFIER_VALUES: dict[str, float] = {
    "dodge_cap": 0.75,
    "resistance_cap": 0.85,
    "shield_block_cap": 0.75,
    "parry_cap": 0.50,
    "counter_attack_cap": 0.50,
    "vampiric_trigger_cap": 1.0,
    "spell_land_chance": 1.0,
    StatKey.STAMINA_REGEN: CONCENTRATION_REGEN_BASE,
}

# Backward-compatible name for old calculator imports.
MODIFIER_RULES = ATTRIBUTE_MODIFIER_RULES
