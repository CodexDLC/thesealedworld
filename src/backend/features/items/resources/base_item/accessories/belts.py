BELTS_DB = {
    "belt": {
        "id": "belt",
        "name_ru": "Пояс",
        "slot": "belt_accessory",
        "type": "accessory",
        "defense_type": "physical",
        "allowed_materials": ["leathers", "cloths"],
        "base_power": 2,
        "base_durability": 40,
        "damage_spread": 0.0,
        "narrative_description": "Пояс держит снаряжение под рукой и помогает распределить вес на ходу.",
        "narrative_tags": ["belt", "accessory", "waist", "quick_slots"],
        "implicit_bonuses": {"quick_slot_capacity": 1.0},
    },
}

__all__ = ["BELTS_DB"]
