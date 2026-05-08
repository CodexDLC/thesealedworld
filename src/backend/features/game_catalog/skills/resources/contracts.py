ACTOR_SNAPSHOT_SKILL_KEYS: tuple[str, ...] = (
    "skill_swords",
    "skill_fencing",
    "skill_polearms",
    "skill_macing",
    "skill_archery",
    "skill_unarmed",
    "skill_one_handed",
    "skill_two_handed",
    "skill_shield_mastery",
    "skill_dual_wield",
    "skill_light_armor",
    "skill_medium_armor",
    "skill_heavy_armor",
    "skill_parrying",
    "skill_anatomy",
    "skill_tactics",
    "skill_adaptation",
)

ENCOUNTER_SKILL_KEYS: tuple[str, ...] = (
    "skill_scouting",
    "skill_pathfinder",
    "skill_hunting",
    "skill_taming",
)

CRAFTING_SKILL_KEYS: tuple[str, ...] = (
    "skill_first_aid",
    "skill_weapon_craft",
    "skill_armor_craft",
    "skill_jewelry_craft",
    "skill_alchemy",
    "skill_engineering",
    "skill_artifact_craft",
)

INVENTORY_SKILL_KEYS: tuple[str, ...] = (
    "skill_swords",
    "skill_fencing",
    "skill_polearms",
    "skill_macing",
    "skill_archery",
    "skill_unarmed",
    "skill_one_handed",
    "skill_two_handed",
    "skill_shield_mastery",
    "skill_dual_wield",
    "skill_light_armor",
    "skill_medium_armor",
    "skill_heavy_armor",
    "skill_parrying",
    "skill_weapon_craft",
    "skill_armor_craft",
    "skill_jewelry_craft",
    "skill_engineering",
)

SKILL_SURFACE_CONTRACTS: dict[str, tuple[str, ...]] = {
    "actor_snapshot": ACTOR_SNAPSHOT_SKILL_KEYS,
    "encounter": ENCOUNTER_SKILL_KEYS,
    "crafting": CRAFTING_SKILL_KEYS,
    "inventory": INVENTORY_SKILL_KEYS,
}


__all__ = [
    "ACTOR_SNAPSHOT_SKILL_KEYS",
    "CRAFTING_SKILL_KEYS",
    "ENCOUNTER_SKILL_KEYS",
    "INVENTORY_SKILL_KEYS",
    "SKILL_SURFACE_CONTRACTS",
]
