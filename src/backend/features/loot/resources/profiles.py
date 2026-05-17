from __future__ import annotations

from src.backend.features.loot.resources.types import (
    EquipmentEntry,
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
        drop=[
            *_bandit_junk,
            EquipmentEntry("hatchet", 0.12),
            EquipmentEntry("dagger", 0.10),
            EquipmentEntry("buckler", 0.08),
            EquipmentEntry("jerkin", 0.08),
        ],
    ),
    "veteran": RoleLootProfile(
        drop=[
            ResourceEntry("currency", 0.85, (4, 14), fixed_tier=0),
            *_bandit_junk[1:],
            EquipmentEntry("mace", 0.16),
            EquipmentEntry("spear", 0.14),
            EquipmentEntry("shortbow", 0.12),
            EquipmentEntry("jerkin", 0.12),
            EquipmentEntry("breeches", 0.08),
        ],
    ),
    "elite": RoleLootProfile(
        drop=[
            ResourceEntry("currency", 0.90, (8, 24), fixed_tier=0),
            *_bandit_junk[1:],
            EquipmentEntry("longsword", 0.20),
            EquipmentEntry("mace", 0.18),
            EquipmentEntry("jerkin", 0.16),
            EquipmentEntry("helmet", 0.12),
        ],
    ),
    "boss": RoleLootProfile(
        drop=[
            ResourceEntry("currency", 0.95, (18, 60), fixed_tier=0),
            *_bandit_junk[1:],
            EquipmentEntry("warhammer", 0.35),
            EquipmentEntry("longsword", 0.30),
            EquipmentEntry("plate_chest", 0.25),
            EquipmentEntry("shield", 0.20),
        ],
    ),
}

_GOBLIN_ROLES = {
    "minion": RoleLootProfile(
        drop=[
            *_goblin_junk,
            EquipmentEntry("dagger", 0.12),
            EquipmentEntry("mace", 0.10),
            EquipmentEntry("knife", 0.10),
            EquipmentEntry("hood", 0.08),
        ],
    ),
    "veteran": RoleLootProfile(
        drop=[
            ResourceEntry("currency", 0.75, (3, 10), fixed_tier=0),
            *_goblin_junk[1:],
            EquipmentEntry("spear", 0.16),
            EquipmentEntry("sling", 0.14),
            EquipmentEntry("shield", 0.12),
            EquipmentEntry("jerkin", 0.12),
        ],
    ),
    "elite": RoleLootProfile(
        drop=[
            ResourceEntry("currency", 0.85, (6, 20), fixed_tier=0),
            *_goblin_junk[1:],
            EquipmentEntry("dagger", 0.20),
            EquipmentEntry("sling", 0.18),
            EquipmentEntry("leather_cap", 0.16),
            EquipmentEntry("jerkin", 0.14),
        ],
    ),
    "boss": RoleLootProfile(
        drop=[
            ResourceEntry("currency", 0.90, (14, 45), fixed_tier=0),
            *_goblin_junk[1:],
            EquipmentEntry("battle_axe", 0.30),
            EquipmentEntry("warhammer", 0.25),
            EquipmentEntry("plate_chest", 0.20),
            EquipmentEntry("helmet", 0.18),
        ],
    ),
}

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
    # Humanoid bandits - basic gear plus tier-0 junk resources.
    # ------------------------------------------------------------------
    "bandit_gang": MonsterLootProfile(
        id="bandit_gang",
        archetype="humanoid",
        roles=_BANDIT_ROLES,
    ),
    # ------------------------------------------------------------------
    # Goblins - scavenged basic gear plus tier-0 junk resources.
    # ------------------------------------------------------------------
    "goblin_tribe": MonsterLootProfile(
        id="goblin_tribe",
        archetype="humanoid",
        roles=_GOBLIN_ROLES,
    ),
    # ------------------------------------------------------------------
    # Legacy alias for older actor sources.
    # ------------------------------------------------------------------
    "humanoid_bandit": MonsterLootProfile(
        id="humanoid_bandit",
        archetype="humanoid",
        roles=_BANDIT_ROLES,
    ),
    # ------------------------------------------------------------------
    # Fallback — minimal drop, no salvage
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
