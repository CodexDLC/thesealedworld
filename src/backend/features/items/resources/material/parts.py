"""
ДЕТАЛИ (Crafting Parts)
=======================
Промежуточные продукты, которые создаются из материалов и используются в сложных рецептах.
"""

PARTS_DB = {
    "blades": {
        1: {
            "id": "part_blade_iron",
            "name_ru": "Железный клинок",
            "name_prefix_ru": "Железный",
            "tier_mult": 1.0,
            "slots": 0,
            "narrative_tags": ["sharp", "forged"],
        },
        2: {
            "id": "part_blade_steel",
            "name_ru": "Стальной клинок",
            "name_prefix_ru": "Стальной",
            "tier_mult": 1.5,
            "slots": 0,
            "narrative_tags": ["razor", "honed"],
        },
    },
    "hilts": {
        1: {
            "id": "part_hilt_oak",
            "name_ru": "Дубовая рукоять",
            "name_prefix_ru": "Дубовый",
            "tier_mult": 1.0,
            "slots": 0,
            "narrative_tags": ["comfortable", "grip"],
        },
        2: {
            "id": "part_hilt_leather",
            "name_ru": "Кожаная рукоять",
            "name_prefix_ru": "Кожаный",
            "tier_mult": 1.2,
            "slots": 0,
            "narrative_tags": ["wrapped", "non_slip"],
        },
    },
}
