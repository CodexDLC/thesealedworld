"""
СЕМЕЙСТВО: ВЛАДЫКИ ЯКОРЕЙ
==========================
Четыре tier-7 силы на границах мира. В обычные затянувшиеся бои приходят их
проекции; истинные тела остаются рейдовыми боссами анкорных разломов.
"""

from ..monster_structs import MonsterFamily

ANCHOR_SOVEREIGNS_FAMILY: MonsterFamily = {
    "id": "anchor_sovereigns",
    "archetype": "unknown",
    "organization_type": "solitary",
    "default_tags": ["anchor", "higher_force", "projection", "raid_boss"],
    "hierarchy": {
        "minions": [],
        "veterans": [],
        "elites": [],
        "boss": [
            "north_stasis_sovereign",
            "south_entropy_sovereign",
            "west_gravity_sovereign",
            "east_evolution_sovereign",
        ],
    },
    "skill_kit": {
        "base": {
            "skill_tactics": 1.0,
            "skill_anatomy": 1.0,
            "skill_parrying": 1.0,
            "skill_adaptation": 1.0,
        },
        "role_bonus": {
            "boss": {
                "skill_leadership": 1.0,
                "skill_team_spirit": 1.0,
            },
        },
    },
    "loot_profile": {
        "salvage_type": "anchor_residue",
        "loot_mode": "hybrid",
        "allowed_loadout_slots": "full_humanoid",
        "equipment_drop_policy": "none",
        "drops_as_equipment": False,
        "materials": ["anchor_shard", "projection_core"],
        "equipment_quality": "tier_7_raid",
    },
    "variants": {
        "north_stasis_sovereign": {
            "id": "north_stasis_sovereign",
            "role": "boss",
            "cost": 2200,
            "min_tier": 7,
            "max_tier": 7,
            "narrative_hint": "Северный якорь стазиса. Его проекция не спешит: она отнимает у боя само движение.",
            "extra_tags": ["north", "stasis", "frost", "time_stasis", "absolute_zero"],
            "base_stats": {
                "strength": 160,
                "agility": 70,
                "endurance": 220,
                "intellect": 190,
                "memory": 240,
                "mental": 210,
                "perception": 150,
                "projection": 80,
                "prediction": 40,
            },
            "fixed_loadout": {
                "main_hand": "anchor_stasis_crown_blade",
                "off_hand": "shield",
                "chest_armor": "anchor_projection_aegis",
            },
            "skill_overrides": {
                "skill_swords": 1.0,
                "skill_one_handed": 1.0,
                "skill_shield_mastery": 1.0,
                "skill_heavy_armor": 1.0,
                "skill_light_armor": 1.0,
            },
        },
        "south_entropy_sovereign": {
            "id": "south_entropy_sovereign",
            "role": "boss",
            "cost": 2400,
            "min_tier": 7,
            "max_tier": 7,
            "narrative_hint": "Южный якорь энтропии. Его проекция завершает спор грубой ценой распада.",
            "extra_tags": ["south", "entropy", "ash_storm", "lava_veins", "thermal_shock"],
            "base_stats": {
                "strength": 240,
                "agility": 80,
                "endurance": 230,
                "intellect": 110,
                "memory": 120,
                "mental": 220,
                "perception": 130,
                "projection": 90,
                "prediction": 30,
            },
            "fixed_loadout": {
                "two_hand": "anchor_entropy_cinder_maul",
                "chest_armor": "anchor_projection_aegis",
            },
            "skill_overrides": {
                "skill_macing": 1.0,
                "skill_two_handed": 1.0,
                "skill_heavy_armor": 1.0,
                "skill_light_armor": 1.0,
            },
        },
        "west_gravity_sovereign": {
            "id": "west_gravity_sovereign",
            "role": "boss",
            "cost": 2100,
            "min_tier": 7,
            "max_tier": 7,
            "narrative_hint": "Западный якорь гравитации. Его проекция выбирает направление, в котором падают враги.",
            "extra_tags": ["west", "gravity", "floating_islands", "reverse_gravity", "lightning"],
            "base_stats": {
                "strength": 130,
                "agility": 210,
                "endurance": 170,
                "intellect": 220,
                "memory": 160,
                "mental": 170,
                "perception": 240,
                "projection": 100,
                "prediction": 90,
            },
            "fixed_loadout": {
                "main_hand": "anchor_gravity_storm_lance",
                "chest_armor": "anchor_projection_aegis",
            },
            "skill_overrides": {
                "skill_polearms": 1.0,
                "skill_one_handed": 1.0,
                "skill_light_armor": 1.0,
                "skill_heavy_armor": 1.0,
            },
        },
        "east_evolution_sovereign": {
            "id": "east_evolution_sovereign",
            "role": "boss",
            "cost": 2300,
            "min_tier": 7,
            "max_tier": 7,
            "narrative_hint": "Восточный якорь эволюции. Его проекция отвечает на застой быстрой мутацией боя.",
            "extra_tags": ["east", "evolution", "living_jungle", "toxic_spores", "mutation_fog"],
            "base_stats": {
                "strength": 170,
                "agility": 230,
                "endurance": 190,
                "intellect": 160,
                "memory": 220,
                "mental": 180,
                "perception": 230,
                "projection": 70,
                "prediction": 120,
            },
            "fixed_loadout": {
                "main_hand": "anchor_evolution_bloom_talons",
                "off_hand": "anchor_evolution_bloom_talons",
                "chest_armor": "anchor_projection_aegis",
            },
            "skill_overrides": {
                "skill_fencing": 1.0,
                "skill_dual_wield": 1.0,
                "skill_light_armor": 1.0,
                "skill_heavy_armor": 1.0,
            },
        },
    },
}
