from src.backend.features.loot.resources import equipment_pool as equipment_pool
from src.backend.features.loot.resources.equipment_pool import get_pool, merged_pool
from src.backend.features.loot.resources.profiles import LOOT_PROFILES
from src.backend.features.loot.resources.resolver import resolve_resource
from src.backend.features.loot.resources.types import (
    FamilyEquipmentProfile,
    LootEntry,
    LootScheme,
    MonsterLootProfile,
    ResourceEntry,
    RoleLootProfile,
)

__all__ = [
    "LOOT_PROFILES",
    "resolve_resource",
    "get_pool",
    "merged_pool",
    "equipment_pool",
    "FamilyEquipmentProfile",
    "LootEntry",
    "LootScheme",
    "MonsterLootProfile",
    "ResourceEntry",
    "RoleLootProfile",
]


def get_profile(profile_id: str) -> MonsterLootProfile:
    return LOOT_PROFILES.get(profile_id) or LOOT_PROFILES["default"]
