"""
СЕМЕЙСТВО: ГОЛЕМЫ (Приказ и неостановимость)
============================================
Логика: приказ -> функция -> неостановимость
"""

from ..monster_structs import MonsterFamily

GOLEMS_FAMILY: MonsterFamily = {
    "id": "golem_foundry",
    "archetype": "construct",
    "organization_type": "solitary",  # TSP Base: 100
    "default_tags": ["construct", "golem", "artificial", "fearless"],
    "hierarchy": {
        "minions": ["stone_construct", "clay_golem"],
        "veterans": ["iron_golem", "war_golem"],
        "elites": ["arcane_golem", "siege_golem"],
        "boss": ["ancient_golem", "colossus"],
    },
    "variants": {
        # --- 1. Конструкты (Minions) [TSP ~100] ---
        "stone_construct": {
            "id": "stone_construct",
            "role": "minion",
            "cost": 20,
            "min_tier": 3,
            "max_tier": 6,
            "narrative_hint": "A roughly hewn stone figure. Moves with a grinding sound.",
            "extra_tags": ["stone", "slow"],
            "base_stats": {
                "strength": 30,
                "agility": 5,
                "endurance": 40,
                "intellect": 1,
                "memory": 1,
                "mental": 20,
                "perception": 6,
                "projection": 1,
                "prediction": 1,  # Итого: 105
            },
            "fixed_loadout": {},
            "skills": ["attack_heavy", "buff_defense"],
        },
        "clay_golem": {
            "id": "clay_golem",
            "role": "minion",
            "cost": 20,
            "min_tier": 3,
            "max_tier": 6,
            "narrative_hint": "A golem made of soft clay. Hits absorb into its body.",
            "extra_tags": ["clay", "regenerating"],
            "base_stats": {
                "strength": 25,
                "agility": 10,
                "endurance": 35,
                "intellect": 1,
                "memory": 1,
                "mental": 20,
                "perception": 6,
                "projection": 1,
                "prediction": 1,  # Итого: 100
            },
            "fixed_loadout": {},
            "skills": ["attack_heavy", "buff_heal"],
        },
        # --- 2. Боевые (Veterans) [TSP ~150] ---
        "iron_golem": {
            "id": "iron_golem",
            "role": "veteran",
            "cost": 50,
            "min_tier": 4,
            "max_tier": 7,
            "narrative_hint": "A towering figure of iron plates and gears. Steam hisses from its joints.",
            "extra_tags": ["iron", "heavy_armor"],
            "base_stats": {
                "strength": 40,
                "agility": 5,
                "endurance": 60,
                "intellect": 2,
                "memory": 2,
                "mental": 20,
                "perception": 8,
                "projection": 1,
                "prediction": 1,  # Итого: 139
            },
            "fixed_loadout": {},
            "skills": ["attack_heavy", "attack_aoe", "buff_defense"],
        },
        "war_golem": {
            "id": "war_golem",
            "role": "veteran",
            "cost": 50,
            "min_tier": 4,
            "max_tier": 7,
            "narrative_hint": "A golem built for war, with blades instead of hands.",
            "extra_tags": ["war", "bladed"],
            "base_stats": {
                "strength": 50,
                "agility": 10,
                "endurance": 50,
                "intellect": 2,
                "memory": 2,
                "mental": 20,
                "perception": 10,
                "projection": 1,
                "prediction": 1,  # Итого: 146
            },
            "fixed_loadout": {},
            "skills": ["attack_aoe", "attack_execute"],
        },
        # --- 3. Специализированные (Elites) [TSP ~250] ---
        "arcane_golem": {
            "id": "arcane_golem",
            "role": "elite",
            "cost": 150,
            "min_tier": 5,
            "max_tier": 8,
            "narrative_hint": "A golem inscribed with glowing runes. Crackles with magical energy.",
            "extra_tags": ["arcane", "magic"],
            "base_stats": {
                "strength": 40,
                "agility": 15,
                "endurance": 60,
                "intellect": 40,
                "memory": 40,
                "mental": 30,
                "perception": 20,
                "projection": 1,
                "prediction": 5,  # Итого: 251
            },
            "fixed_loadout": {},
            "skills": ["attack_ranged", "buff_defense", "buff_rage"],
        },
        "siege_golem": {
            "id": "siege_golem",
            "role": "elite",
            "cost": 150,
            "min_tier": 5,
            "max_tier": 8,
            "narrative_hint": "A massive golem designed to break walls. Slow but unstoppable.",
            "extra_tags": ["siege", "heavy"],
            "base_stats": {
                "strength": 80,
                "agility": 2,
                "endurance": 100,
                "intellect": 2,
                "memory": 2,
                "mental": 30,
                "perception": 6,
                "projection": 1,
                "prediction": 1,  # Итого: 224 (чистая мощь)
            },
            "fixed_loadout": {},
            "skills": ["attack_heavy", "attack_aoe", "attack_ranged"],
        },
        # --- 4. Реликты (Bosses) [TSP ~400] ---
        "ancient_golem": {
            "id": "ancient_golem",
            "role": "boss",
            "cost": 600,
            "min_tier": 6,
            "max_tier": 9,
            "narrative_hint": "A golem from a lost civilization. Its core still hums with power.",
            "extra_tags": ["ancient", "relic", "laser"],
            "base_stats": {
                "strength": 80,
                "agility": 10,
                "endurance": 120,
                "intellect": 20,
                "memory": 20,
                "mental": 50,
                "perception": 30,
                "projection": 5,
                "prediction": 10,  # Итого: 345
            },
            "fixed_loadout": {},
            "skills": ["attack_ranged", "buff_heal", "debuff_slow", "summon_minion"],
        },
        "colossus": {
            "id": "colossus",
            "role": "boss",
            "cost": 600,
            "min_tier": 6,
            "max_tier": 9,
            "narrative_hint": "A golem the size of a building. Its footsteps cause earthquakes.",
            "extra_tags": ["colossal", "world_ender"],
            "base_stats": {
                "strength": 150,
                "agility": 2,
                "endurance": 200,
                "intellect": 5,
                "memory": 5,
                "mental": 50,
                "perception": 10,
                "projection": 5,
                "prediction": 5,  # Итого: 432
            },
            "fixed_loadout": {},
            "skills": ["attack_aoe", "attack_aoe", "attack_aoe", "buff_defense"],
        },
    },
}
