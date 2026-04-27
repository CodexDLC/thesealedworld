"""
ЭКИПИРОВКА МОНСТРОВ: ГУМАНОИДЫ (Вампиры, Эльфы, Ящеры)
======================================================
Здесь остаются только УНИКАЛЬНЫЕ предметы, недоступные игрокам.
"""

HUMANOIDS_EQUIPMENT = {
    # --- Уникальное оружие боссов ---
    "demon_blade": {
        "id": "demon_blade",
        "name_ru": "Клинок Демона",
        "slot": "main_hand",
        "type": "weapon",
        "base_power": 15,  # Было 30
        "damage_spread": 0.1,
        "implicit_bonuses": {"lifesteal": 0.10, "physical_damage_bonus": 0.20},
    },
    "shadow_daggers": {
        "id": "shadow_daggers",
        "name_ru": "Теневые кинжалы",
        "slot": "main_hand",
        "type": "weapon",
        "base_power": 10,  # Было 20
        "damage_spread": 0.0,
        "implicit_bonuses": {"attack_speed": 0.30, "stealth_bonus": 0.50},
    },
    "void_staff": {
        "id": "void_staff",
        "name_ru": "Посох Пустоты",
        "slot": "main_hand",
        "type": "weapon",
        "base_power": 12,  # Было 25
        "damage_spread": 0.0,
        "implicit_bonuses": {"magical_damage_bonus": 0.50, "debuff_weaken": 0.20},
    },
    # --- Уникальная броня/материалы ---
    "adamantite_plate": {
        "id": "adamantite_plate",
        "name_ru": "Адамантитовая броня",
        "slot": "chest_armor",
        "type": "armor",
        "base_power": 15,  # Было 30
        "implicit_bonuses": {"physical_resistance": 0.30},
    },
    # --- Экзотика (пока здесь) ---
    "blowgun": {
        "id": "blowgun",
        "name_ru": "Духовая трубка",
        "slot": "main_hand",
        "type": "weapon",
        "base_power": 1,  # Было 2
        "damage_spread": 0.0,
        "implicit_bonuses": {"poison_damage_bonus": 0.50},
    },
}
