"""
ЭКИПИРОВКА МОНСТРОВ: НЕЖИТЬ
===========================
"""

UNDEAD_EQUIPMENT = {
    "grimoire": {
        "id": "grimoire",
        "name_ru": "Гримуар",
        "slot": "off_hand",
        "type": "weapon",  # Используется как магический фокус
        "base_power": 5,
        "damage_spread": 0.0,
        "implicit_bonuses": {
            "magical_damage_bonus": 0.15,
            "intelligence": 5,
        },
    },
}
