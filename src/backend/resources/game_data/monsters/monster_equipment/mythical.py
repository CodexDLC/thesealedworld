"""
ЭКИПИРОВКА МОНСТРОВ: МИФИЧЕСКИЕ (Ангелы, Демоны)
================================================
"""

MYTHICAL_EQUIPMENT = {
    # --- Ангелы ---
    "tower_shield": {
        "id": "tower_shield",
        "name_ru": "Башенный щит",
        "slot": "off_hand",
        "type": "shield",
        "base_power": 25,
        "implicit_bonuses": {"shield_block_chance": 0.30, "shield_block_power": 0.50},
    },
    "flaming_sword": {
        "id": "flaming_sword",
        "name_ru": "Пылающий меч",
        "slot": "main_hand",
        "type": "weapon",
        "base_power": 30,
        "damage_spread": 0.1,
        "implicit_bonuses": {"magical_damage_bonus": 0.30, "fire_damage_bonus": 0.20},
    },
    "scepter_light": {
        "id": "scepter",  # Общий ключ
        "name_ru": "Скипетр Света",
        "slot": "main_hand",
        "type": "weapon",
        "base_power": 20,
        "damage_spread": 0.0,
        "implicit_bonuses": {"magical_damage_bonus": 0.40, "healing_power": 0.20},
    },
    "morningstar": {
        "id": "morningstar",
        "name_ru": "Моргенштерн",
        "slot": "main_hand",
        "type": "weapon",
        "base_power": 35,
        "damage_spread": 0.2,
        "implicit_bonuses": {"physical_penetration": 0.30},
    },
    "sword_of_light": {
        "id": "sword_of_light",
        "name_ru": "Меч Света",
        "slot": "main_hand",
        "type": "weapon",
        "base_power": 50,
        "damage_spread": 0.0,
        "implicit_bonuses": {"magical_damage_bonus": 1.0},
    },
    # --- Демоны ---
    "whip": {
        "id": "whip",
        "name_ru": "Кнут",
        "slot": "main_hand",
        "type": "weapon",
        "base_power": 20,
        "damage_spread": 0.1,
        "implicit_bonuses": {"attack_speed": 0.20, "bleed_chance": 0.15},
    },
    "scepter_dark": {
        "id": "scepter",  # Общий ключ
        "name_ru": "Скипетр Тьмы",
        "slot": "main_hand",
        "type": "weapon",
        "base_power": 25,
        "damage_spread": 0.0,
        "implicit_bonuses": {"magical_damage_bonus": 0.50, "lifesteal": 0.10},
    },
    "sword_of_damnation": {
        "id": "sword_of_damnation",
        "name_ru": "Меч Проклятия",
        "slot": "main_hand",
        "type": "weapon",
        "base_power": 60,
        "damage_spread": 0.1,
        "implicit_bonuses": {"physical_damage_bonus": 0.50, "debuff_weaken": 0.20},
    },
}
