from enum import Enum


class StatKey(str, Enum):
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
    CRIT_CHANCE = "crit_chance"
    CRIT_POWER = "crit_power"
    ACCURACY = "accuracy"
    ARMOR_PENETRATION = "armor_penetration"

    # Defense
    ARMOR = "armor"
    EVASION = "evasion"  # или DODGE
    BLOCK = "block"
    PARRY = "parry"
    MAGIC_RESIST = "magic_resist"

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
    HAND_SIZE = "hand_size"
