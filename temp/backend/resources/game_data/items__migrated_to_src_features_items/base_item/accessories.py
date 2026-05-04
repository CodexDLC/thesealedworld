"""
РУКОВОДСТВО ПО ЗАПОЛНЕНИЮ: АКСЕССУАРЫ
=====================================

Этот файл содержит шаблоны для бижутерии и поясов.
Это "болванки" предметов. Все магические свойства (бонусы) добавляются
через эссенции (аффиксы) во время крафта.

КЛЮЧЕВЫЕ ПОЛЯ:
---------------
- slot: 'ring_1', 'ring_2', 'amulet', 'earring', 'belt_accessory'.
- base_power: Обычно 0, так как основная сила в бонусах.
- implicit_bonuses: Врожденные бонусы. Для аксессуаров они обычно пустые,
  кроме особых случаев (например, пояс дает слоты).
"""

from typing import Any

ACCESSORIES_DB: dict[str, dict[str, dict[str, Any]]] = {
    "accessories": {
        # ==========================================
        # БАЗОВЫЕ ПРЕДМЕТЫ (Тир 0)
        # ==========================================
        "ring": {
            "id": "ring",
            "name_ru": "Кольцо",
            "slot": "ring_1",
            "extra_slots": ["ring_2"],
            "damage_type": None,
            "defense_type": None,
            "allowed_materials": ["ingots"],
            "base_power": 0,
            "base_durability": 100,
            "damage_spread": 0.0,
            "narrative_tags": ["ring", "jewelry", "band"],
            "implicit_bonuses": {},
        },
        "amulet": {
            "id": "amulet",
            "name_ru": "Амулет",
            "slot": "amulet",
            "damage_type": None,
            "defense_type": None,
            "allowed_materials": ["ingots", "woods"],
            "base_power": 0,
            "base_durability": 100,
            "damage_spread": 0.0,
            "narrative_tags": ["amulet", "necklace", "pendant"],
            "implicit_bonuses": {},
        },
        "earring": {
            "id": "earring",
            "name_ru": "Серьга",
            "slot": "earring",
            "damage_type": None,
            "defense_type": None,
            "allowed_materials": ["ingots"],
            "base_power": 0,
            "base_durability": 100,
            "damage_spread": 0.0,
            "narrative_tags": ["earring", "jewelry", "stud"],
            "implicit_bonuses": {},
        },
        # --- ЕДИНЫЙ БАЗОВЫЙ ПОЯС ---
        "belt": {
            "id": "belt",
            "name_ru": "Пояс",
            "slot": "belt_accessory",
            "damage_type": None,
            "defense_type": "physical",
            "allowed_materials": ["leathers", "cloths"],
            "base_power": 1,
            "base_durability": 40,
            "damage_spread": 0.0,
            "narrative_tags": ["belt", "waist", "strap"],
            "implicit_bonuses": {
                "quick_slot_capacity": 1.0  # Пояс всегда дает хотя бы 1 слот
            },
        },
    },
}
