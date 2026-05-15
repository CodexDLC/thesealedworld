"""
СЕМЕЙСТВО: ДРАКОНЫ (Территория и доминирование)
===============================================
Логика: территория -> давление -> доминирование
"""

from ..monster_structs import MonsterFamily

DRAGONS_FAMILY: MonsterFamily = {
    "id": "dragon_lair",
    "archetype": "beast",
    "organization_type": "solitary",  # TSP Base: 100
    "default_tags": ["beast", "dragon", "scale", "fire"],
    "hierarchy": {
        "minions": ["drake_whelp", "wingless_drake"],
        "veterans": ["sky_drake", "ash_drake"],
        "elites": ["ancient_drake", "elemental_drake"],
        "boss": ["dragon_lord", "world_dragon"],
    },
    "variants": {
        # --- 1. Молодняк (Minions) [TSP ~100] ---
        "drake_whelp": {
            "id": "drake_whelp",
            "role": "minion",
            "cost": 20,
            "min_tier": 5,
            "max_tier": 8,
            "narrative_hint": "A small dragon, barely larger than a dog. Snaps its jaws aggressively.",
            "extra_tags": ["young", "fire"],
            "base_stats": {
                "strength": 20,
                "agility": 25,
                "endurance": 20,
                "intelligence": 10,
                "wisdom": 10,
                "men": 15,
                "perception": 15,
                "charisma": 5,
                "luck": 5,  # Итого: 125
            },
            "fixed_loadout": {},
            "skills": ["attack_basic", "debuff_burn"],
        },
        "wingless_drake": {
            "id": "wingless_drake",
            "role": "minion",
            "cost": 20,
            "min_tier": 5,
            "max_tier": 8,
            "narrative_hint": "A muscular, flightless drake. Charges with reckless abandon.",
            "extra_tags": ["grounded", "brute"],
            "base_stats": {
                "strength": 35,
                "agility": 15,
                "endurance": 35,
                "intelligence": 5,
                "wisdom": 5,
                "men": 15,
                "perception": 10,
                "charisma": 4,
                "luck": 5,  # Итого: 129
            },
            "fixed_loadout": {},
            "skills": ["attack_aoe"],
        },
        # --- 2. Охотники (Veterans) [TSP ~150] ---
        "sky_drake": {
            "id": "sky_drake",
            "role": "veteran",
            "cost": 50,
            "min_tier": 6,
            "max_tier": 9,
            "narrative_hint": "A sleek drake with wide wings. Dives from the sky.",
            "extra_tags": ["flying", "fast"],
            "base_stats": {
                "strength": 30,
                "agility": 40,
                "endurance": 30,
                "intelligence": 15,
                "wisdom": 15,
                "men": 20,
                "perception": 25,
                "charisma": 10,
                "luck": 5,  # Итого: 190
            },
            "fixed_loadout": {},
            "skills": ["attack_heavy", "attack_aoe", "attack_heavy"],
        },
        "ash_drake": {
            "id": "ash_drake",
            "role": "veteran",
            "cost": 50,
            "min_tier": 6,
            "max_tier": 9,
            "narrative_hint": "A drake covered in soot and ash. Its scales glow with inner heat.",
            "extra_tags": ["fire", "ash"],
            "base_stats": {
                "strength": 40,
                "agility": 25,
                "endurance": 40,
                "intelligence": 12,
                "wisdom": 12,
                "men": 25,
                "perception": 20,
                "charisma": 8,
                "luck": 5,  # Итого: 187
            },
            "fixed_loadout": {},
            "skills": ["attack_aoe", "debuff_blind", "debuff_burn"],
        },
        # --- 3. Доминирующие (Elites) [TSP ~250] ---
        "ancient_drake": {
            "id": "ancient_drake",
            "role": "elite",
            "cost": 150,
            "min_tier": 7,
            "max_tier": 10,
            "narrative_hint": "A massive drake with thick, scarred scales. Moves with heavy purpose.",
            "extra_tags": ["ancient", "heavy_armor", "tough"],
            "base_stats": {
                "strength": 60,
                "agility": 15,
                "endurance": 70,
                "intelligence": 20,
                "wisdom": 20,
                "men": 40,
                "perception": 25,
                "charisma": 20,
                "luck": 5,  # Итого: 275
            },
            "fixed_loadout": {},
            "skills": ["attack_heavy", "debuff_weaken", "buff_defense"],
        },
        "elemental_drake": {
            "id": "elemental_drake",
            "role": "elite",
            "cost": 150,
            "min_tier": 7,
            "max_tier": 10,
            "narrative_hint": "A drake infused with raw elemental energy (fire, ice, or lightning).",
            "extra_tags": ["elemental", "magic"],
            "base_stats": {
                "strength": 50,
                "agility": 35,
                "endurance": 50,
                "intelligence": 30,
                "wisdom": 30,
                "men": 40,
                "perception": 30,
                "charisma": 15,
                "luck": 5,  # Итого: 285
            },
            "fixed_loadout": {},
            "skills": ["attack_aoe", "attack_aoe", "attack_aoe"],
        },
        # --- 4. Вершины (Bosses) [TSP ~400] ---
        "dragon_lord": {
            "id": "dragon_lord",
            "role": "boss",
            "cost": 600,
            "min_tier": 8,
            "max_tier": 11,
            "narrative_hint": "A true dragon of immense size and intelligence. Rules the region.",
            "extra_tags": ["lord", "leader", "ancient"],
            "base_stats": {
                "strength": 80,
                "agility": 40,
                "endurance": 100,
                "intelligence": 60,
                "wisdom": 60,
                "men": 80,
                "perception": 50,
                "charisma": 60,
                "luck": 20,  # Итого: 550
            },
            "fixed_loadout": {},
            "skills": ["attack_aoe", "attack_aoe", "attack_heavy", "debuff_weaken"],
        },
        "world_dragon": {
            "id": "world_dragon",
            "role": "boss",
            "cost": 600,
            "min_tier": 8,
            "max_tier": 11,
            "narrative_hint": "A creature so large it is mistaken for a mountain range. Its awakening changes the world.",
            "extra_tags": ["colossal", "world_ender"],
            "base_stats": {
                "strength": 150,
                "agility": 20,
                "endurance": 200,
                "intelligence": 50,
                "wisdom": 50,
                "men": 100,
                "perception": 40,
                "charisma": 50,
                "luck": 20,  # Итого: 680
            },
            "fixed_loadout": {},
            "skills": ["special_unique", "special_unique", "special_unique"],
        },
    },
}
