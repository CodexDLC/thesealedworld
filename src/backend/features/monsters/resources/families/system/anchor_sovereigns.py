"""
СЕМЕЙСТВО: ВЛАДЫКИ ЯКОРЕЙ
==========================
Системная семья для четырех tier-7 сил на границах мира. В обычные
затянувшиеся бои приходят их проекции; истинные тела остаются рейдовыми
боссами анкорных разломов.
"""

from ...monster_structs import MonsterFamily

ANCHOR_SOVEREIGNS_FAMILY: MonsterFamily = {
    "id": "anchor_sovereigns",
    "resource_version": 1,
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
            "spawn_weight": 2200,
            "min_tier": 7,
            "max_tier": 7,
            "narrative_hint": "Северный якорь стазиса. Его проекция не спешит: она отнимает у боя само движение.",
            "extra_tags": ["north", "stasis", "frost", "time_stasis", "absolute_zero"],
            "base_stats": {
                "strength": 161,
                "agility": 71,
                "endurance": 221,
                "intellect": 191,
                "memory": 241,
                "mental": 211,
                "perception": 151,
                "projection": 81,
                "prediction": 41,
            },
            "fixed_loadout": {
                "main_hand": "anchor_stasis_crown_blade",
                "off_hand": "shield",
                "chest_armor": "anchor_projection_aegis",
            },
            "skills": [
                "skill_swords",
                "skill_shield_mastery",
                "skill_heavy_armor",
                "skill_light_armor",
                "skill_tactics",
                "skill_anatomy",
                "skill_parrying",
            ],
        },
        "south_entropy_sovereign": {
            "id": "south_entropy_sovereign",
            "role": "boss",
            "spawn_weight": 2400,
            "min_tier": 7,
            "max_tier": 7,
            "narrative_hint": "Южный якорь энтропии. Его проекция завершает спор грубой ценой распада.",
            "extra_tags": ["south", "entropy", "ash_storm", "lava_veins", "thermal_shock"],
            "base_stats": {
                "strength": 241,
                "agility": 81,
                "endurance": 231,
                "intellect": 111,
                "memory": 121,
                "mental": 221,
                "perception": 131,
                "projection": 91,
                "prediction": 31,
            },
            "fixed_loadout": {
                "two_hand": "anchor_entropy_cinder_maul",
                "chest_armor": "anchor_projection_aegis",
            },
            "skills": [
                "skill_macing",
                "skill_two_handed",
                "skill_heavy_armor",
                "skill_light_armor",
                "skill_tactics",
                "skill_anatomy",
                "skill_parrying",
            ],
        },
        "west_gravity_sovereign": {
            "id": "west_gravity_sovereign",
            "role": "boss",
            "spawn_weight": 2100,
            "min_tier": 7,
            "max_tier": 7,
            "narrative_hint": "Западный якорь гравитации. Его проекция выбирает направление, в котором падают враги.",
            "extra_tags": ["west", "gravity", "floating_islands", "reverse_gravity", "lightning"],
            "base_stats": {
                "strength": 131,
                "agility": 211,
                "endurance": 171,
                "intellect": 221,
                "memory": 161,
                "mental": 171,
                "perception": 241,
                "projection": 101,
                "prediction": 91,
            },
            "fixed_loadout": {
                "main_hand": "anchor_gravity_storm_lance",
                "chest_armor": "anchor_projection_aegis",
            },
            "skills": [
                "skill_polearms",
                "skill_light_armor",
                "skill_heavy_armor",
                "skill_tactics",
                "skill_anatomy",
                "skill_parrying",
            ],
        },
        "east_evolution_sovereign": {
            "id": "east_evolution_sovereign",
            "role": "boss",
            "spawn_weight": 2300,
            "min_tier": 7,
            "max_tier": 7,
            "narrative_hint": "Восточный якорь эволюции. Его проекция отвечает на застой быстрой мутацией боя.",
            "extra_tags": ["east", "evolution", "living_jungle", "toxic_spores", "mutation_fog"],
            "base_stats": {
                "strength": 171,
                "agility": 231,
                "endurance": 191,
                "intellect": 161,
                "memory": 221,
                "mental": 181,
                "perception": 231,
                "projection": 71,
                "prediction": 121,
            },
            "fixed_loadout": {
                "main_hand": "anchor_evolution_bloom_talons",
                "off_hand": "anchor_evolution_bloom_talons",
                "chest_armor": "anchor_projection_aegis",
            },
            "skills": [
                "skill_fencing",
                "skill_dual_wield",
                "skill_light_armor",
                "skill_heavy_armor",
                "skill_tactics",
                "skill_anatomy",
                "skill_parrying",
            ],
        },
    },
}

__all__ = ["ANCHOR_SOVEREIGNS_FAMILY"]
