"""
ТКАНИ (Woven Fiber)
===================
Материалы категории "cloths". Создаются из волокон.
"""

CLOTHS_DB = {
    "cloths": {
        0: {
            "id": "mat_dirty_rags",
            "name_ru": "Грязное тряпье",
            "tier_mult": 0.8,
            "slots": 0,
            "narrative_tags": ["dirty", "rags"],
        },
        1: {
            "id": "mat_linen",
            "name_ru": "Льняная ткань",
            "tier_mult": 1.0,
            "slots": 2,  # Ткань имеет бонус к магии (больше слотов)
            "narrative_tags": ["linen", "clean", "white"],
        },
        2: {
            "id": "mat_strong_silk",
            "name_ru": "Прочный шелк",
            "tier_mult": 1.3,
            "slots": 3,
            "narrative_tags": ["silk", "strong", "light"],
        },
        3: {
            "id": "mat_infused_cloth",
            "name_ru": "Зачарованная ткань",
            "tier_mult": 1.8,
            "slots": 4,
            "narrative_tags": ["infused", "glowing", "mana"],
        },
        4: {
            "id": "mat_golden_fleece",
            "name_ru": "Золотое руно",
            "tier_mult": 2.5,
            "slots": 5,
            "narrative_tags": ["golden", "fleece", "warm", "mythical"],
        },
        5: {
            "id": "mat_spectral_cloth",
            "name_ru": "Призрачная ткань",
            "tier_mult": 3.5,
            "slots": 5,
            "narrative_tags": ["spectral", "ethereal", "translucent"],
        },
        6: {
            "id": "mat_void_weave",
            "name_ru": "Ткань Пустоты",
            "tier_mult": 5.0,
            "slots": 6,
            "narrative_tags": ["void", "dark", "absorbing"],
        },
        7: {
            "id": "mat_celestial_silk",
            "name_ru": "Небесный шелк",
            "tier_mult": 6.5,
            "slots": 7,
            "narrative_tags": ["celestial", "starlight", "divine"],
        },
    },
}
