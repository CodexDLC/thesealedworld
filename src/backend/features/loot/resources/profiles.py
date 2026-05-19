from __future__ import annotations

from src.backend.features.loot.resources.types import (
    FamilyEquipmentProfile,
    MonsterLootProfile,
    ResourceEntry,
    RoleLootProfile,
)

# ---------------------------------------------------------------------------
# Beast profiles
# drop:    fixed_tier=0 (junk), no skill needed
# salvage: fixed_tier=None (resolved by monster tier ±1), skinning skill
# spoil:   empty until spoil skill is implemented
# ---------------------------------------------------------------------------

_rat_drop = [
    ResourceEntry("hide", 0.70, (1, 1), fixed_tier=0),
    ResourceEntry("bones", 0.60, (1, 1)),
    ResourceEntry("currency", 0.40, (1, 1)),
]

_wolf_drop = [
    ResourceEntry("hide", 0.70, (1, 1), fixed_tier=0),
    ResourceEntry("bones", 0.60, (1, 2)),
    ResourceEntry("currency", 0.40, (1, 1)),
]

_bandit_junk = [
    ResourceEntry("currency", 0.80, (2, 8), fixed_tier=0),
    ResourceEntry("res_dirty_rags", 0.55, (1, 2), fixed_tier=0),
    ResourceEntry("res_rust_flakes", 0.35, (1, 2), fixed_tier=0),
]

_goblin_junk = [
    ResourceEntry("currency", 0.70, (1, 6), fixed_tier=0),
    ResourceEntry("res_dirty_rags", 0.60, (1, 3), fixed_tier=0),
    ResourceEntry("res_rust_flakes", 0.45, (1, 3), fixed_tier=0),
    ResourceEntry("res_charcoal", 0.25, (1, 1), fixed_tier=0),
]

_BANDIT_ROLES = {
    "minion": RoleLootProfile(
        drop=[*_bandit_junk],
    ),
    "veteran": RoleLootProfile(
        drop=[
            ResourceEntry("currency", 0.85, (4, 14), fixed_tier=0),
            *_bandit_junk[1:],
        ],
    ),
    "elite": RoleLootProfile(
        drop=[
            ResourceEntry("currency", 0.90, (8, 24), fixed_tier=0),
            *_bandit_junk[1:],
        ],
    ),
    "boss": RoleLootProfile(
        drop=[
            ResourceEntry("currency", 0.95, (18, 60), fixed_tier=0),
            *_bandit_junk[1:],
        ],
    ),
}

_GOBLIN_ROLES = {
    "minion": RoleLootProfile(
        drop=[*_goblin_junk],
    ),
    "veteran": RoleLootProfile(
        drop=[
            ResourceEntry("currency", 0.75, (3, 10), fixed_tier=0),
            *_goblin_junk[1:],
        ],
    ),
    "elite": RoleLootProfile(
        drop=[
            ResourceEntry("currency", 0.85, (6, 20), fixed_tier=0),
            *_goblin_junk[1:],
        ],
    ),
    "boss": RoleLootProfile(
        drop=[
            ResourceEntry("currency", 0.90, (14, 45), fixed_tier=0),
            *_goblin_junk[1:],
        ],
    ),
}

# Equipment pool configs — families own which subcategories can drop and at what rates
_BANDIT_EQUIPMENT = FamilyEquipmentProfile(
    enabled_subcategories=("fencing", "macing", "polearms", "archery", "offhand", "armor_medium"),
    role_chances={"minion": 0.18, "veteran": 0.25, "elite": 0.35, "boss": 0.55},
)

_GOBLIN_EQUIPMENT = FamilyEquipmentProfile(
    enabled_subcategories=("fencing", "macing", "archery", "offhand", "armor_light", "armor_medium"),
    role_chances={"minion": 0.15, "veteran": 0.22, "elite": 0.30, "boss": 0.50},
)

LOOT_PROFILES: dict[str, MonsterLootProfile] = {
    # ------------------------------------------------------------------
    # Rats — small beast, tier 0 hide, salvage x1
    # ------------------------------------------------------------------
    "rat_swarm": MonsterLootProfile(
        id="rat_swarm",
        archetype="beast",
        roles={
            "minion": RoleLootProfile(
                drop=_rat_drop,
                salvage=[ResourceEntry("hide", 0.70, (1, 1))],
            ),
            "veteran": RoleLootProfile(
                drop=_rat_drop,
                salvage=[ResourceEntry("hide", 0.75, (1, 1))],
            ),
            "elite": RoleLootProfile(
                drop=_rat_drop,
                salvage=[ResourceEntry("hide", 0.80, (1, 1))],
            ),
            "boss": RoleLootProfile(
                drop=[
                    ResourceEntry("hide", 0.80, (1, 2), fixed_tier=0),
                    ResourceEntry("bones", 0.70, (1, 3)),
                    ResourceEntry("currency", 0.60, (2, 5)),
                ],
                salvage=[ResourceEntry("hide", 0.90, (1, 2))],
            ),
        },
    ),
    # ------------------------------------------------------------------
    # Wolves — medium beast, tier 1 hide, salvage x1-2
    # ------------------------------------------------------------------
    "wolf_pack": MonsterLootProfile(
        id="wolf_pack",
        archetype="beast",
        roles={
            "minion": RoleLootProfile(
                drop=_wolf_drop,
                salvage=[ResourceEntry("hide", 0.80, (1, 2))],
            ),
            "veteran": RoleLootProfile(
                drop=_wolf_drop,
                salvage=[ResourceEntry("hide", 0.80, (1, 2))],
            ),
            "elite": RoleLootProfile(
                drop=_wolf_drop,
                salvage=[ResourceEntry("hide", 0.85, (1, 2))],
            ),
            "boss": RoleLootProfile(
                drop=[
                    ResourceEntry("hide", 0.80, (2, 3), fixed_tier=0),
                    ResourceEntry("bones", 0.70, (2, 4)),
                    ResourceEntry("currency", 0.60, (3, 8)),
                ],
                salvage=[ResourceEntry("hide", 0.90, (2, 3))],
            ),
        },
    ),
    # ------------------------------------------------------------------
    # Humanoid bandits - junk resources + pool-based equipment drops
    # ------------------------------------------------------------------
    "bandit_gang": MonsterLootProfile(
        id="bandit_gang",
        archetype="humanoid",
        roles=_BANDIT_ROLES,
        equipment=_BANDIT_EQUIPMENT,
    ),
    # ------------------------------------------------------------------
    # Goblins - junk resources + pool-based equipment drops
    # ------------------------------------------------------------------
    "goblin_tribe": MonsterLootProfile(
        id="goblin_tribe",
        archetype="humanoid",
        roles=_GOBLIN_ROLES,
        equipment=_GOBLIN_EQUIPMENT,
    ),
    # ------------------------------------------------------------------
    # Legacy alias for older actor sources.
    # ------------------------------------------------------------------
    "humanoid_bandit": MonsterLootProfile(
        id="humanoid_bandit",
        archetype="humanoid",
        roles=_BANDIT_ROLES,
        equipment=_BANDIT_EQUIPMENT,
    ),
    # ------------------------------------------------------------------
    # Fallback — minimal drop, no salvage, no equipment
    # ------------------------------------------------------------------
    "default": MonsterLootProfile(
        id="default",
        archetype="beast",
        roles={
            "minion": RoleLootProfile(
                drop=[ResourceEntry("currency", 0.50, (1, 5))],
            ),
        },
    ),
}
