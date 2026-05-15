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
    # Humanoid bandit — equipment drop, no salvage/spoil
    # ------------------------------------------------------------------
    "humanoid_bandit": MonsterLootProfile(
        id="humanoid_bandit",
        archetype="humanoid",
        roles={
            "minion": RoleLootProfile(
                drop=[
                    ResourceEntry("currency", 0.90, (5, 20)),
                    EquipmentEntry("sword_iron", 0.20),
                    EquipmentEntry("armor_leather", 0.15),
                ],
            ),
            "veteran": RoleLootProfile(
                drop=[
                    ResourceEntry("currency", 0.90, (10, 40)),
                    EquipmentEntry("sword_iron", 0.25),
                    EquipmentEntry("armor_leather", 0.20),
                ],
            ),
            "elite": RoleLootProfile(
                drop=[
                    ResourceEntry("currency", 0.90, (20, 80)),
                    EquipmentEntry("sword_iron", 0.30),
                    EquipmentEntry("armor_leather", 0.25),
                ],
            ),
            "boss": RoleLootProfile(
                drop=[
                    ResourceEntry("currency", 0.95, (50, 200)),
                    EquipmentEntry("sword_iron", 0.50),
                    EquipmentEntry("armor_leather", 0.40),
                ],
            ),
        },
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
