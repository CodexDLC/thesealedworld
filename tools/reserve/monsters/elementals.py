"""
СЕМЕЙСТВО: ЭЛЕМЕНТАЛИ (Среда и разрушение)
==========================================
Логика: среда -> форма -> разрушение
"""

from ..monster_structs import MonsterFamily

ELEMENTALS_FAMILY: MonsterFamily = {
    "id": "elemental_rift",
    "archetype": "construct",
    "organization_type": "solitary",  # TSP Base: 100
    "default_tags": ["elemental", "magic", "chaos"],
    "hierarchy": {
        "minions": ["elemental_spark", "elemental_wisp"],
        "veterans": ["fire_elemental", "ice_elemental"],
        "elites": ["greater_elemental", "raging_elemental"],
        "boss": ["elemental_lord", "primal_avatar"],
    },
    "variants": {
        # --- 1. Проявления (Minions) [TSP ~100] ---
        "elemental_spark": {
            "id": "elemental_spark",
            "role": "minion",
            "cost": 20,
            "min_tier": 3,
            "max_tier": 6,
            "narrative_hint": "A tiny, flickering mote of elemental energy. Moves erratically.",
            "extra_tags": ["spark", "weak"],
            "base_stats": {
                "strength": 5,
                "agility": 40,
                "endurance": 10,
                "intelligence": 10,
                "wisdom": 10,
                "men": 20,
                "perception": 10,
                "charisma": 1,
                "luck": 10,  # Итого: 116
            },
            "fixed_loadout": {},
            "skills": ["attack_ranged"],
        },
        "elemental_wisp": {
            "id": "elemental_wisp",
            "role": "minion",
            "cost": 20,
            "min_tier": 3,
            "max_tier": 6,
            "narrative_hint": "A floating ball of light and energy. Seems curious but dangerous.",
            "extra_tags": ["wisp", "energy"],
            "base_stats": {
                "strength": 5,
                "agility": 30,
                "endurance": 15,
                "intelligence": 15,
                "wisdom": 15,
                "men": 20,
                "perception": 15,
                "charisma": 5,
                "luck": 8,  # Итого: 128
            },
            "fixed_loadout": {},
            "skills": ["attack_lifesteal", "debuff_blind"],
        },
        # --- 2. Стабильные формы (Veterans) [TSP ~150] ---
        "fire_elemental": {
            "id": "fire_elemental",
            "role": "veteran",
            "cost": 50,
            "min_tier": 4,
            "max_tier": 7,
            "narrative_hint": "A humanoid shape made of roaring flames. Burns everything it touches.",
            "extra_tags": ["fire", "burn"],
            "base_stats": {
                "strength": 30,
                "agility": 20,
                "endurance": 30,
                "intelligence": 20,
                "wisdom": 20,
                "men": 30,
                "perception": 15,
                "charisma": 1,
                "luck": 5,  # Итого: 171
            },
            "fixed_loadout": {},
            "skills": ["attack_ranged", "debuff_burn", "attack_heavy"],
        },
        "ice_elemental": {
            "id": "ice_elemental",
            "role": "veteran",
            "cost": 50,
            "min_tier": 4,
            "max_tier": 7,
            "narrative_hint": "A jagged construct of ice and snow. Radiates intense cold.",
            "extra_tags": ["ice", "cold", "freeze"],
            "base_stats": {
                "strength": 40,
                "agility": 10,
                "endurance": 40,
                "intelligence": 20,
                "wisdom": 20,
                "men": 30,
                "perception": 15,
                "charisma": 1,
                "luck": 5,  # Итого: 181
            },
            "fixed_loadout": {},
            "skills": ["attack_ranged", "debuff_stun", "attack_heavy"],
        },
        # --- 3. Усиленные (Elites) [TSP ~250] ---
        "greater_elemental": {
            "id": "greater_elemental",
            "role": "elite",
            "cost": 150,
            "min_tier": 5,
            "max_tier": 8,
            "narrative_hint": "A massive elemental, its form stable and imposing. Commands the lesser spirits.",
            "extra_tags": ["greater", "leader"],
            "base_stats": {
                "strength": 60,
                "agility": 20,
                "endurance": 60,
                "intelligence": 30,
                "wisdom": 30,
                "men": 40,
                "perception": 20,
                "charisma": 10,
                "luck": 5,  # Итого: 275
            },
            "fixed_loadout": {},
            "skills": ["attack_aoe", "summon_minion", "attack_heavy"],
        },
        "raging_elemental": {
            "id": "raging_elemental",
            "role": "elite",
            "cost": 150,
            "min_tier": 5,
            "max_tier": 8,
            "narrative_hint": "An elemental in a state of chaotic flux, exploding with power.",
            "extra_tags": ["raging", "unstable", "explosive"],
            "base_stats": {
                "strength": 50,
                "agility": 40,
                "endurance": 40,
                "intelligence": 20,
                "wisdom": 20,
                "men": 50,
                "perception": 20,
                "charisma": 1,
                "luck": 10,  # Итого: 251
            },
            "fixed_loadout": {},
            "skills": ["explode_on_death", "special_unique", "attack_aoe"],
        },
        # --- 4. Аватары (Bosses) [TSP ~400] ---
        "elemental_lord": {
            "id": "elemental_lord",
            "role": "boss",
            "cost": 600,
            "min_tier": 6,
            "max_tier": 9,
            "narrative_hint": "A god-like entity composed of pure elemental force. Rules a plane of existence.",
            "extra_tags": ["lord", "ancient", "ruler"],
            "base_stats": {
                "strength": 80,
                "agility": 40,
                "endurance": 80,
                "intelligence": 60,
                "wisdom": 60,
                "men": 80,
                "perception": 40,
                "charisma": 40,
                "luck": 20,  # Итого: 500
            },
            "fixed_loadout": {},
            "skills": ["special_unique", "summon_minion", "special_unique"],
        },
        "primal_avatar": {
            "id": "primal_avatar",
            "role": "boss",
            "cost": 600,
            "min_tier": 6,
            "max_tier": 9,
            "narrative_hint": "The living embodiment of nature's wrath. A storm given form.",
            "extra_tags": ["primal", "avatar", "nature"],
            "base_stats": {
                "strength": 100,
                "agility": 60,
                "endurance": 100,
                "intelligence": 40,
                "wisdom": 50,
                "men": 100,
                "perception": 50,
                "charisma": 30,
                "luck": 30,  # Итого: 560
            },
            "fixed_loadout": {},
            "skills": ["special_unique", "attack_aoe", "attack_aoe", "attack_aoe"],
        },
    },
}
