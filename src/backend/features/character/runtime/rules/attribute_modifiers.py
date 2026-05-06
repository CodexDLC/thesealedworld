from __future__ import annotations

from src.shared.enums.stats_enums import StatKey

# Attribute -> combat modifier bridge used when a combat actor snapshot is calculated.
# AC stores plain attribute values; combat raw keeps them as {base, source, temp}.
ATTRIBUTE_MODIFIER_RULES: dict[str, dict[str, float]] = {
    # Damage
    StatKey.PHYSICAL_DAMAGE: {StatKey.STRENGTH: 1.0},
    StatKey.MAGICAL_DAMAGE: {StatKey.INTELLECT: 1.0},
    # Accuracy, penetration, crit
    StatKey.ACCURACY: {StatKey.PERCEPTION: 0.02, StatKey.PREDICTION: 0.01},
    StatKey.ARMOR_PENETRATION: {StatKey.PERCEPTION: 0.01},
    StatKey.CRIT_CHANCE: {StatKey.PREDICTION: 0.02},
    StatKey.CRIT_POWER: {StatKey.MEMORY: 0.01},
    # Defense
    StatKey.EVASION: {StatKey.AGILITY: 0.015, StatKey.PREDICTION: 0.005},
    StatKey.ARMOR: {StatKey.ENDURANCE: 0.5},
    StatKey.BLOCK: {StatKey.STRENGTH: 0.02},
    StatKey.PARRY: {StatKey.AGILITY: 0.02},
    StatKey.MAGIC_RESIST: {StatKey.MENTAL: 0.01},
    # Vitals
    StatKey.HP: {StatKey.ENDURANCE: 10.0, StatKey.STRENGTH: 2.0},
    StatKey.EN: {StatKey.MENTAL: 5.0, StatKey.ENDURANCE: 2.0},
    StatKey.STAMINA: {StatKey.ENDURANCE: 10.0},
    StatKey.HP_REGEN: {StatKey.ENDURANCE: 0.1},
    StatKey.EN_REGEN: {StatKey.MENTAL: 0.1},
    StatKey.STAMINA_REGEN: {StatKey.ENDURANCE: 0.2},
    # Speed
    StatKey.INITIATIVE: {StatKey.PREDICTION: 1.0, StatKey.AGILITY: 0.5},
    StatKey.ATTACK_SPEED: {StatKey.AGILITY: 0.005},
    StatKey.CAST_SPEED: {StatKey.MEMORY: 0.005},
    StatKey.MOVEMENT_SPEED: {StatKey.AGILITY: 0.01},
}

DEFAULT_MODIFIER_VALUES: dict[str, float] = {
    "dodge_cap": 0.75,
    "resistance_cap": 0.85,
    "shield_block_cap": 0.75,
    "parry_cap": 0.50,
    "counter_attack_cap": 0.50,
    "vampiric_trigger_cap": 1.0,
    "spell_land_chance": 1.0,
}

# Backward-compatible name for old calculator imports.
MODIFIER_RULES = ATTRIBUTE_MODIFIER_RULES
