JEWELRY_DB = {
    "ring": {
        "id": "ring",
        "name_ru": "Кольцо",
        "slot": "ring_1",
        "extra_slots": ["ring_2"],
        "type": "accessory",
        "allowed_materials": ["ingots"],
        "base_power": 0,
        "base_durability": 100,
        "damage_spread": 0.0,
        "narrative_description": "Простое кольцо как основа для печати, символа или вложенной силы.",
        "narrative_tags": ["ring", "accessory", "jewelry"],
        "implicit_bonuses": {},
    },
    "amulet": {
        "id": "amulet",
        "name_ru": "Амулет",
        "slot": "amulet",
        "type": "accessory",
        "allowed_materials": ["ingots", "woods"],
        "base_power": 0,
        "base_durability": 100,
        "damage_spread": 0.0,
        "narrative_description": "Амулет висит у груди и легко становится фокусом личной защиты.",
        "narrative_tags": ["amulet", "accessory", "necklace", "pendant"],
        "implicit_bonuses": {"debuff_avoidance": 0.03},
    },
}

__all__ = ["JEWELRY_DB"]
