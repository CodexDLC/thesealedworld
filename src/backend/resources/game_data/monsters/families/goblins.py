"""
СЕМЕЙСТВО: ГОБЛИНЫ (Техно-хаос и выживание)
=========================================
Логика: хитрость -> инструменты -> взрыв
"""

from ..monster_structs import MonsterFamily

GOBLINS_FAMILY: MonsterFamily = {
    "id": "goblin_tribe",
    "archetype": "humanoid",
    "organization_type": "horde",  # TSP Base: 30
    "default_tags": ["goblin", "small", "cunning", "tinkerer"],
    "hierarchy": {
        "minions": ["goblin_sneak", "goblin_scavenger"],
        "veterans": ["goblin_spearman", "goblin_slinger"],
        "elites": ["goblin_tinkerer", "goblin_bomber"],
        "boss": ["goblin_chief", "scrap_king"],
    },
    "variants": {
        # --- 1. Мелочь (Minions) [TSP ~30] ---
        "goblin_sneak": {
            "id": "goblin_sneak",
            "role": "minion",
            "cost": 20,
            "min_tier": 0,
            "max_tier": 4,
            "narrative_hint": "A small goblin with a hooded cloak and a pair of sharp daggers, moves silently.",
            "extra_tags": ["stealth", "assassin"],
            "base_stats": {
                "strength": 4,
                "agility": 12,
                "endurance": 4,
                "intelligence": 4,
                "wisdom": 2,
                "men": 2,
                "perception": 6,
                "charisma": 1,
                "luck": 5,  # Итого: 40 (чуть выше базы из-за luck/agi)
            },
            "fixed_loadout": {"main_hand": "dagger", "off_hand": "dagger", "chest_garment": "shirt"},
            "skills": ["attack_heavy", "stealth"],
        },
        "goblin_scavenger": {
            "id": "goblin_scavenger",
            "role": "minion",
            "cost": 20,
            "min_tier": 0,
            "max_tier": 4,
            "narrative_hint": "A goblin carrying a large, overflowing backpack. Wields a simple club.",
            "extra_tags": ["scavenger", "hoarder"],
            "base_stats": {
                "strength": 6,
                "agility": 6,
                "endurance": 6,
                "intelligence": 4,
                "wisdom": 2,
                "men": 2,
                "perception": 4,
                "charisma": 1,
                "luck": 4,  # Итого: 35
            },
            "fixed_loadout": {"main_hand": "mace", "chest_garment": "shirt"},
            "skills": ["debuff_armor_break"],
        },
        # --- 2. Бойцы (Veterans) [TSP ~45] ---
        "goblin_spearman": {
            "id": "goblin_spearman",
            "role": "veteran",
            "cost": 50,
            "min_tier": 0,
            "max_tier": 5,
            "narrative_hint": "A disciplined goblin with a long spear and a crude wooden shield.",
            "extra_tags": ["infantry", "shield"],
            "base_stats": {
                "strength": 8,
                "agility": 8,
                "endurance": 10,
                "intelligence": 4,
                "wisdom": 3,
                "men": 4,
                "perception": 6,
                "charisma": 2,
                "luck": 3,  # Итого: 48
            },
            "fixed_loadout": {"main_hand": "spear", "off_hand": "shield", "chest_armor": "jerkin"},
            "skills": ["attack_pierce", "buff_defense"],
        },
        "goblin_slinger": {
            "id": "goblin_slinger",
            "role": "veteran",
            "cost": 50,
            "min_tier": 1,
            "max_tier": 5,
            "narrative_hint": "A fast goblin with a sling, constantly moving and throwing rocks.",
            "extra_tags": ["ranged", "fast"],
            "base_stats": {
                "strength": 4,
                "agility": 14,
                "endurance": 6,
                "intelligence": 4,
                "wisdom": 4,
                "men": 3,
                "perception": 8,
                "charisma": 2,
                "luck": 4,  # Итого: 49
            },
            "fixed_loadout": {"main_hand": "sling", "chest_garment": "shirt"},
            "skills": ["attack_ranged"],
        },
        # --- 3. Инженеры (Elites) [TSP ~75] ---
        "goblin_tinkerer": {
            "id": "goblin_tinkerer",
            "role": "elite",
            "cost": 150,
            "min_tier": 2,
            "max_tier": 6,
            "narrative_hint": "A goblin with goggles and a belt full of tools. Throws caltrops and sets traps.",
            "extra_tags": ["engineer", "trapper"],
            "base_stats": {
                "strength": 6,
                "agility": 12,
                "endurance": 10,
                "intelligence": 15,
                "wisdom": 8,
                "men": 6,
                "perception": 12,
                "charisma": 4,
                "luck": 6,  # Итого: 79
            },
            "fixed_loadout": {"main_hand": "dagger", "chest_garment": "apron", "head_armor": "goggles"},
            "skills": ["special_trap", "debuff_slow"],
        },
        "goblin_bomber": {
            "id": "goblin_bomber",
            "role": "elite",
            "cost": 150,
            "min_tier": 2,
            "max_tier": 6,
            "narrative_hint": "A goblin with a manic grin and a sack of crude explosives.",
            "extra_tags": ["bomber", "explosives", "reckless"],
            "base_stats": {
                "strength": 8,
                "agility": 12,
                "endurance": 12,
                "intelligence": 10,
                "wisdom": 4,
                "men": 8,
                "perception": 8,
                "charisma": 4,
                "luck": 10,  # Итого: 76
            },
            "fixed_loadout": {"chest_armor": "jerkin"},
            "skills": ["attack_aoe", "explode_on_death"],
        },
        # --- 4. Вожди (Bosses) [TSP ~120] ---
        "goblin_chief": {
            "id": "goblin_chief",
            "role": "boss",
            "cost": 600,
            "min_tier": 3,
            "max_tier": 7,
            "narrative_hint": "A larger, smarter goblin wearing a crude crown and better armor. Shouts commands.",
            "extra_tags": ["leader", "commander"],
            "base_stats": {
                "strength": 18,
                "agility": 14,
                "endurance": 20,
                "intelligence": 10,
                "wisdom": 10,
                "men": 12,
                "perception": 12,
                "charisma": 12,
                "luck": 8,  # Итого: 116
            },
            "fixed_loadout": {"main_hand": "battle_axe", "chest_armor": "plate_chest", "head_armor": "helmet"},
            "skills": ["buff_rage", "attack_aoe", "attack_execute"],
        },
        "scrap_king": {
            "id": "scrap_king",
            "role": "boss",
            "cost": 600,
            "min_tier": 4,
            "max_tier": 7,
            "narrative_hint": "A huge goblin sitting on a throne of junk, wearing a makeshift power armor.",
            "extra_tags": ["king", "heavy_armor", "engineer"],
            "base_stats": {
                "strength": 25,
                "agility": 8,
                "endurance": 30,
                "intelligence": 15,
                "wisdom": 10,
                "men": 15,
                "perception": 10,
                "charisma": 15,
                "luck": 5,  # Итого: 133
            },
            "fixed_loadout": {
                "main_hand": "warhammer",
                "chest_armor": "plate_chest",
                "head_armor": "helmet",
                "arms_armor": "gauntlets",
                "legs_armor": "greaves",
            },
            "skills": ["attack_ranged", "debuff_stun", "buff_rage"],
        },
    },
}
