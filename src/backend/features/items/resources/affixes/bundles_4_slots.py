"""
БАНДЛЫ НА 4 СЛОТА (Легендарные)
===============================
Самые мощные и редкие сеты эффектов, определяющие билд.
"""

BUNDLES_4_SLOTS = {
    # --- УНИКАЛЬНЫЕ ВОИНСКИЕ ---
    "world_breaker": {
        "id": "world_breaker",
        "ingredient_id": "essence_world_fragment",
        "cost_slots": 4,
        "min_tier": 4,
        "effects": ["phys_dmg_flat", "phys_penetration", "crit_power", "hp_max"],
        "narrative_tags": ["world_breaker", "shattering", "apocalyptic"],
    },
    # --- УНИКАЛЬНЫЕ МАГИЧЕСКИЕ ---
    "comet_caller": {
        "id": "comet_caller",
        "ingredient_id": "essence_starlight",
        "cost_slots": 4,
        "min_tier": 4,
        "effects": ["magic_dmg_pct", "magic_penetration", "fire_dmg", "energy_max"],
        "narrative_tags": ["comet", "celestial", "starfall"],
    },
    # --- УНИКАЛЬНЫЕ ЗАЩИТНЫЕ ---
    "unmovable_object": {
        "id": "unmovable_object",
        "ingredient_id": "essence_mountain_heart",
        "cost_slots": 4,
        "min_tier": 4,
        "effects": ["phys_resist", "magic_resist", "hp_max", "thorns"],
        "narrative_tags": ["unmovable", "fortress", "bastion"],
    },
    # --- УНИКАЛЬНЫЕ ГИБРИДНЫЕ ---
    "void_touch": {
        "id": "void_touch",
        "ingredient_id": "essence_void_fragment",
        "cost_slots": 4,
        "min_tier": 4,
        "effects": ["magic_penetration", "vampirism", "dodge", "energy_regen"],
        "narrative_tags": ["void", "touch", "entropy"],
    },
    "dragon_aspect": {
        "id": "dragon_aspect",
        "ingredient_id": "essence_dragon_scale",
        "cost_slots": 4,
        "min_tier": 4,
        "effects": ["fire_dmg", "fire_res", "hp_max", "thorns"],
        "narrative_tags": ["dragon", "aspect", "inferno"],
    },
}
