from enum import StrEnum


class StatKey(StrEnum):
    """
    Ключи всех характеристик персонажа (Attributes, Vitals, Secondary).
    Используются в формулах, Redis и DTO.
    """

    # --- 1. PRIMARY ATTRIBUTES (9 Base) ---
    # Body
    STRENGTH = "strength"
    AGILITY = "agility"
    ENDURANCE = "endurance"
    # Core
    INTELLECT = "intellect"
    MEMORY = "memory"
    MENTAL = "mental"  # или WISDOM
    # Sensor
    PERCEPTION = "perception"
    PROJECTION = "projection"
    PREDICTION = "prediction"

    # --- 2. VITALS (Resources) ---
    HP = "hp"
    EN = "en"  # Energy (основной ресурс для абилок)
    STAMINA = "stamina"  # Выносливость (для физических действий, бега)

    # --- 3. COMBAT STATS (Secondary) ---
    # Offense
    PHYSICAL_DAMAGE = "physical_damage"
    MAGICAL_DAMAGE = "magical_damage"
    MAGICAL_PENETRATION = "magical_penetration"
    CRIT_CHANCE = "crit_chance"
    CRIT_POWER = "crit_power"
    ACCURACY = "accuracy"
    PHYSICAL_SUPPRESSION = "physical_suppression"
    ARMOR_PENETRATION_PCT = "armor_penetration_pct"
    ARMOR_PENETRATION_FLAT = "armor_penetration_flat"
    ARMOR_IGNORE_CHANCE = "armor_ignore_chance"

    # Defense
    ARMOR = "armor"
    EVASION = "evasion"  # или DODGE
    BLOCK = "block"
    PARRY = "parry"
    PHYSICAL_RESISTANCE = "physical_resistance"
    MAGIC_RESIST = "magic_resist"
    ANTI_DODGE_CHANCE = "anti_dodge_chance"

    # Speed & Time
    INITIATIVE = "initiative"
    ATTACK_SPEED = "attack_speed"
    CAST_SPEED = "cast_speed"
    MOVEMENT_SPEED = "movement_speed"
    CRAFTING_SPEED = "crafting_speed"

    # --- 4. REGEN ---
    HP_REGEN = "hp_regen"
    EN_REGEN = "en_regen"
    STAMINA_REGEN = "stamina_regen"

    # --- 5. SPECIAL ---
    COUNTER_ATTACK_CHANCE = "counter_attack_chance"
    HAND_SIZE = "hand_size"

    # --- 6. STATUS / ENVIRONMENT RESISTANCES ---
    CONTROL_RESISTANCE = "control_resistance"
    MENTAL_RESISTANCE = "mental_resistance"
    POISON_RESISTANCE = "poison_resistance"
    BLEED_RESISTANCE = "bleed_resistance"
    ENVIRONMENT_BIO_RESISTANCE = "environment_bio_resistance"

    FIRE_RESISTANCE = "fire_resistance"
    WATER_RESISTANCE = "water_resistance"
    AIR_RESISTANCE = "air_resistance"
    EARTH_RESISTANCE = "earth_resistance"
    LIGHT_RESISTANCE = "light_resistance"
    DARK_RESISTANCE = "dark_resistance"
    ARCANE_RESISTANCE = "arcane_resistance"
    NATURE_RESISTANCE = "nature_resistance"
