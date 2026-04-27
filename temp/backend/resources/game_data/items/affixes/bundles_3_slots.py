"""
БАНДЛЫ НА 3 СЛОТА (Эпические)
=============================
Улучшенные версии 2-слотовых бандлов, добавляющие третий синергирующий эффект.
"""

BUNDLES_3_SLOTS = {
    # --- ВОИН / БРУТАЛ (Эволюция) ---
    "warlord": {
        "id": "warlord",
        "ingredient_id": "essence_conqueror_seal",
        "cost_slots": 3,
        "min_tier": 3,
        "effects": ["phys_dmg_flat", "hp_max", "phys_accuracy"],  # Soldier + Accuracy
        "narrative_tags": ["warlord", "commander", "unyielding"],
    },
    "berserker": {
        "id": "berserker",
        "ingredient_id": "essence_rage_heart",
        "cost_slots": 3,
        "min_tier": 3,
        "effects": ["phys_dmg_flat", "crit_power", "crit_chance"],  # Barbarian + Crit Chance
        "narrative_tags": ["berserker", "fury", "unstoppable"],
    },
    # --- ВОР / ЛОВКАЧ (Эволюция) ---
    "assassin": {
        "id": "assassin",
        "ingredient_id": "essence_night_shade",
        "cost_slots": 3,
        "min_tier": 3,
        "effects": ["crit_chance", "dodge", "phys_penetration"],  # Thief + Penetration
        "narrative_tags": ["assassin", "silent", "deadly"],
    },
    "swordmaster": {
        "id": "swordmaster",
        "ingredient_id": "essence_master_grip",
        "cost_slots": 3,
        "min_tier": 3,
        "effects": ["phys_accuracy", "parry", "crit_chance"],  # Duelist + Crit Chance
        "narrative_tags": ["swordmaster", "blade_dancer", "perfect_strike"],
    },
    # --- ТАНК / ЗАЩИТНИК (Эволюция) ---
    "juggernaut": {
        "id": "juggernaut",
        "ingredient_id": "essence_adamant_core",
        "cost_slots": 3,
        "min_tier": 3,
        "effects": ["phys_resist", "block_chance", "hp_max"],  # Guardian + HP
        "narrative_tags": ["juggernaut", "colossus", "immovable"],
    },
    "troll": {
        "id": "troll",
        "ingredient_id": "essence_troll_blood",
        "cost_slots": 3,
        "min_tier": 3,
        "effects": ["hp_max", "hp_regen", "phys_resist"],  # Bear + Phys Resist
        "narrative_tags": ["troll", "regenerating", "undying"],
    },
    # --- МАГ / КАСТЕР (Эволюция) ---
    "archmage": {
        "id": "archmage",
        "ingredient_id": "essence_arcane_crystal",
        "cost_slots": 3,
        "min_tier": 3,
        "effects": ["magic_dmg_pct", "energy_max", "magic_penetration"],  # Scholar + Magic Pen
        "narrative_tags": ["archmage", "arcane", "powerful"],
    },
    "lich": {
        "id": "lich",
        "ingredient_id": "essence_phylactery_dust",
        "cost_slots": 3,
        "min_tier": 3,
        "effects": ["magic_resist", "energy_regen", "vampirism"],  # Mystic + Vampirism
        "narrative_tags": ["lich", "undead", "soul_drain"],
    },
    # --- СПЕЦИАЛЬНЫЕ (Эволюция) ---
    "dragon_hoard": {
        "id": "dragon_hoard",
        "ingredient_id": "essence_dragon_tear",
        "cost_slots": 3,
        "min_tier": 3,
        "effects": ["loot_chance", "craft_speed", "fire_res"],  # Merchant + Fire Resist
        "narrative_tags": ["dragon_hoard", "treasure", "greedy"],
    },
}
