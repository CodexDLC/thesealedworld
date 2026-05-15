from __future__ import annotations

from typing import Literal, cast

MonsterItemAffixKind = Literal["weapon", "armor", "shield"]
MonsterRole = Literal["minion", "veteran", "elite", "boss"]

MONSTER_AFFIX_COUNT_BY_ROLE: dict[MonsterRole, int] = {
    "minion": 1,
    "veteran": 2,
    "elite": 3,
    "boss": 4,
}

MONSTER_AFFIX_STEP_COUNT_BY_TIER: dict[int, int] = {
    0: 2,
    1: 3,
    2: 4,
    3: 5,
    4: 7,
    5: 9,
    6: 11,
    7: 14,
}

_BEAST_WEAPON_POOL: tuple[str, ...] = (
    "weapon_accuracy",
    "crit_chance",
    "armor_penetration_pct_bonus",
    "control_chance_bonus",
)

_BEAST_ARMOR_POOL: tuple[str, ...] = (
    "evasion_bonus",
    "physical_resistance_bonus",
    "hp_bonus",
    "hp_regen_bonus",
    "control_resistance_bonus",
    "bio_resistance_bonus",
    "thorns_damage_bonus",
    "armor_flat",
)

_HUMANOID_WEAPON_POOL: tuple[str, ...] = (
    "weapon_accuracy",
    "crit_chance",
    "armor_penetration_pct_bonus",
    "control_chance_bonus",
)

_HUMANOID_ARMOR_POOL: tuple[str, ...] = (
    "armor_flat",
    "physical_resistance_bonus",
    "hp_bonus",
    "hp_regen_bonus",
    "control_resistance_bonus",
    "evasion_bonus",
    "thorns_damage_bonus",
    "heat_resistance_bonus",
)

_HUMANOID_SHIELD_POOL: tuple[str, ...] = (
    "block_bonus",
    "shield_guard_power_bonus",
    "armor_flat",
    "physical_resistance_bonus",
    "evasion_bonus",
    "control_resistance_bonus",
    "hp_bonus",
)

MONSTER_AFFIX_POOLS: dict[str, dict[MonsterItemAffixKind, tuple[str, ...]]] = {
    "rat_swarm": {
        "weapon": _BEAST_WEAPON_POOL,
        "armor": _BEAST_ARMOR_POOL,
        "shield": (),
    },
    "wolf_pack": {
        "weapon": _BEAST_WEAPON_POOL,
        "armor": _BEAST_ARMOR_POOL,
        "shield": (),
    },
    "bandit_gang": {
        "weapon": _HUMANOID_WEAPON_POOL,
        "armor": _HUMANOID_ARMOR_POOL,
        "shield": _HUMANOID_SHIELD_POOL,
    },
    "goblin_tribe": {
        "weapon": _HUMANOID_WEAPON_POOL,
        "armor": _HUMANOID_ARMOR_POOL,
        "shield": _HUMANOID_SHIELD_POOL,
    },
}

MONSTER_BOSS_FORCED_AFFIX_SETS: dict[str, dict[str, tuple[str, ...]]] = {
    "rat_swarm": {
        "main_hand": ("weapon_accuracy", "crit_chance", "armor_penetration_pct_bonus", "control_chance_bonus"),
        "off_hand": ("off_hand_accuracy", "crit_chance", "armor_penetration_pct_bonus", "control_chance_bonus"),
        "chest_armor": ("evasion_bonus", "physical_resistance_bonus", "hp_regen_bonus", "bio_resistance_bonus"),
    },
    "wolf_pack": {
        "main_hand": ("weapon_accuracy", "crit_chance", "armor_penetration_pct_bonus", "control_chance_bonus"),
        "off_hand": ("off_hand_accuracy", "crit_chance", "armor_penetration_pct_bonus", "control_chance_bonus"),
        "chest_armor": ("evasion_bonus", "physical_resistance_bonus", "hp_bonus", "hp_regen_bonus"),
    },
    "bandit_gang": {
        "main_hand": ("weapon_accuracy", "crit_chance", "armor_penetration_pct_bonus", "control_chance_bonus"),
        "off_hand": ("off_hand_accuracy", "crit_chance", "armor_penetration_pct_bonus", "control_chance_bonus"),
        "chest_armor": ("armor_flat", "physical_resistance_bonus", "hp_bonus", "control_resistance_bonus"),
    },
    "goblin_tribe": {
        "main_hand": ("weapon_accuracy", "crit_chance", "armor_penetration_pct_bonus", "control_chance_bonus"),
        "off_hand": ("off_hand_accuracy", "crit_chance", "armor_penetration_pct_bonus", "evasion_bonus"),
        "chest_armor": ("evasion_bonus", "physical_resistance_bonus", "hp_bonus", "thorns_damage_bonus"),
    },
}


def get_monster_affix_pool(family_id: str, item_kind: MonsterItemAffixKind) -> tuple[str, ...]:
    return MONSTER_AFFIX_POOLS.get(family_id, {}).get(item_kind, ())


def get_monster_allowed_affixes(family_id: str, item_kind: MonsterItemAffixKind, slot: str) -> tuple[str, ...]:
    base_pool = get_monster_affix_pool(family_id, item_kind)
    if item_kind == "weapon" and slot == "off_hand":
        return tuple(dict.fromkeys((*base_pool, "off_hand_accuracy")))
    return base_pool


def get_monster_affix_count(role: str) -> int:
    return MONSTER_AFFIX_COUNT_BY_ROLE.get(cast("MonsterRole", role), MONSTER_AFFIX_COUNT_BY_ROLE["minion"])


def get_monster_affix_step_count(member_tier: int) -> int:
    safe_tier = max(0, min(7, member_tier))
    return MONSTER_AFFIX_STEP_COUNT_BY_TIER[safe_tier]


def get_monster_boss_forced_affixes(family_id: str, slot: str) -> tuple[str, ...]:
    return MONSTER_BOSS_FORCED_AFFIX_SETS.get(family_id, {}).get(slot, ())
