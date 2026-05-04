"""
ДРЕВЕСИНА (Processed Wood)
==========================
Материалы категории "woods". Создаются из бревен.
"""

WOODS_DB = {
    # --- ДОСКИ (Для щитов, древкового оружия, строительства) ---
    "woods": {
        0: {
            "id": "mat_driftwood_plank",
            "name_ru": "Доска из плавника",
            "tier_mult": 0.8,
            "slots": 0,
            "narrative_tags": ["driftwood", "brittle", "salty"],
        },
        1: {
            "id": "mat_oak_plank",
            "name_ru": "Дубовая доска",
            "tier_mult": 1.0,
            "slots": 1,
            "narrative_tags": ["oak", "solid", "wooden"],
        },
        2: {
            "id": "mat_ironwood_plank",
            "name_ru": "Доска из железного дерева",
            "tier_mult": 1.4,
            "slots": 1,
            "narrative_tags": ["ironwood", "hard", "dark"],
        },
        3: {
            "id": "mat_scorched_plank",
            "name_ru": "Опаленная доска",
            "tier_mult": 2.0,
            "slots": 2,
            "narrative_tags": ["scorched", "ash", "fire_resistant"],
        },
        4: {
            "id": "mat_crystal_infused_wood",
            "name_ru": "Кристаллическая древесина",
            "tier_mult": 2.8,
            "slots": 3,
            "narrative_tags": ["crystal", "infused", "glowing"],
        },
        5: {
            "id": "mat_spirit_wood",
            "name_ru": "Призрачная древесина",
            "tier_mult": 3.8,
            "slots": 3,
            "narrative_tags": ["spirit", "ethereal", "lightweight"],
        },
        6: {
            "id": "mat_void_timber",
            "name_ru": "Брус Пустоты",
            "tier_mult": 5.2,
            "slots": 4,
            "narrative_tags": ["void", "dark", "warped"],
        },
        7: {
            "id": "mat_ancient_heartwood",
            "name_ru": "Древняя сердцевина",
            "tier_mult": 6.8,
            "slots": 5,
            "narrative_tags": ["heartwood", "ancient", "world_tree"],
        },
    },
    # --- ЗАГОТОВКИ ДЛЯ ЛУКОВ (Bow Staves) ---
    "bow_staves": {
        0: {
            "id": "mat_driftwood_stave",
            "name_ru": "Кривая палка",
            "tier_mult": 0.8,
            "slots": 0,
            "narrative_tags": ["crooked", "weak"],
        },
        1: {
            "id": "mat_oak_stave",
            "name_ru": "Дубовая заготовка",
            "tier_mult": 1.0,
            "slots": 1,
            "narrative_tags": ["flexible", "sturdy"],
        },
        2: {
            "id": "mat_ironwood_stave",
            "name_ru": "Заготовка из железного дерева",
            "tier_mult": 1.5,  # Луки из железного дерева мощнее
            "slots": 1,
            "narrative_tags": ["heavy_draw", "powerful"],
        },
        3: {
            "id": "mat_scorched_stave",
            "name_ru": "Опаленная дуга",
            "tier_mult": 2.1,
            "slots": 2,
            "narrative_tags": ["warm", "snapping"],
        },
        4: {
            "id": "mat_crystal_stave",
            "name_ru": "Кристальная дуга",
            "tier_mult": 3.0,
            "slots": 3,
            "narrative_tags": ["resonating", "singing"],
        },
        5: {
            "id": "mat_spirit_stave",
            "name_ru": "Призрачная дуга",
            "tier_mult": 4.0,
            "slots": 3,
            "narrative_tags": ["silent", "swift"],
        },
        6: {
            "id": "mat_void_stave",
            "name_ru": "Дуга Пустоты",
            "tier_mult": 5.5,
            "slots": 4,
            "narrative_tags": ["hungry", "dark_draw"],
        },
        7: {
            "id": "mat_ancient_stave",
            "name_ru": "Древняя дуга",
            "tier_mult": 7.2,
            "slots": 5,
            "narrative_tags": ["legendary", "god_killer"],
        },
    },
}
