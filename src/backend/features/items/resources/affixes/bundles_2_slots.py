"""
БАНДЛЫ НА 2 СЛОТА (Редкие)
==========================
Базовые архетипы классов и стилей игры.
"""

BUNDLES_2_SLOTS = {
    # --- ВОИН / БРУТАЛ ---
    "soldier": {
        "id": "soldier",
        "ingredient_id": "essence_iron_will",
        "cost_slots": 2,
        "min_tier": 1,
        "effects": ["phys_dmg_flat", "hp_max"],
        "narrative_tags": ["soldier", "reliable", "military"],
    },
    "barbarian": {
        "id": "barbarian",
        "ingredient_id": "essence_rage_spark",
        "cost_slots": 2,
        "min_tier": 1,
        "effects": ["phys_dmg_flat", "crit_power"],  # Бьет больно, если кританет
        "narrative_tags": ["barbarian", "wild", "savage"],
    },
    # --- ВОР / ЛОВКАЧ ---
    "thief": {
        "id": "thief",
        "ingredient_id": "essence_shadow_dust",
        "cost_slots": 2,
        "min_tier": 1,
        "effects": ["crit_chance", "dodge"],
        "narrative_tags": ["thief", "sneaky", "agile"],
    },
    "duelist": {
        "id": "duelist",
        "ingredient_id": "essence_wind_feather",
        "cost_slots": 2,
        "min_tier": 1,
        "effects": ["phys_accuracy", "parry"],
        "narrative_tags": ["duelist", "fencing", "elegant"],
    },
    # --- ТАНК / ЗАЩИТНИК ---
    "guardian": {
        "id": "guardian",
        "ingredient_id": "essence_stone_heart",
        "cost_slots": 2,
        "min_tier": 1,
        "effects": ["phys_resist", "block_chance"],
        "narrative_tags": ["guardian", "shield", "protector"],
    },
    "bear": {
        "id": "bear",
        "ingredient_id": "essence_bear_paw",
        "cost_slots": 2,
        "min_tier": 1,
        "effects": ["hp_max", "hp_regen"],
        "narrative_tags": ["bear", "tough", "furry"],
    },
    # --- МАГ / КАСТЕР ---
    "scholar": {
        "id": "scholar",
        "ingredient_id": "essence_mana_drop",
        "cost_slots": 2,
        "min_tier": 1,
        "effects": ["magic_dmg_pct", "energy_max"],
        "narrative_tags": ["scholar", "learned", "bookish"],
    },
    "mystic": {
        "id": "mystic",
        "ingredient_id": "essence_void_wisp",
        "cost_slots": 2,
        "min_tier": 1,
        "effects": ["magic_resist", "energy_regen"],
        "narrative_tags": ["mystic", "warded", "glowing"],
    },
    # --- СПЕЦИАЛЬНЫЕ ---
    "vampire": {
        "id": "vampire",
        "ingredient_id": "essence_blood_vial",
        "cost_slots": 2,
        "min_tier": 2,
        "effects": ["vampirism", "phys_dmg_flat"],
        "narrative_tags": ["vampire", "blood", "crimson"],
    },
    "merchant": {
        "id": "merchant",
        "ingredient_id": "essence_gold_coin",
        "cost_slots": 2,
        "min_tier": 1,
        "effects": ["loot_chance", "craft_speed"],
        "narrative_tags": ["merchant", "wealthy", "golden"],
    },
}
