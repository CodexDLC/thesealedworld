from src.backend.features.loot.resources.profiles import LOOT_PROFILES
from src.backend.features.loot.resources.resolver import resolve_resource
from src.backend.features.loot.resources.types import (
    EquipmentEntry,
    LootEntry,
    LootScheme,
    MonsterLootProfile,
    ResourceEntry,
    RoleLootProfile,
)

__all__ = [
    "LOOT_PROFILES",
    "resolve_resource",
    "EquipmentEntry",
    "LootEntry",
    "LootScheme",
    "MonsterLootProfile",
    "ResourceEntry",
    "RoleLootProfile",
]


def get_profile(profile_id: str) -> MonsterLootProfile:
    return LOOT_PROFILES.get(profile_id) or LOOT_PROFILES["default"]
