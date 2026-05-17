from __future__ import annotations

import pytest

from src.backend.features.items.resources import get_base_by_id
from src.backend.features.loot.resources.profiles import LOOT_PROFILES
from src.backend.features.loot.resources.resolver import resolve_resource
from src.backend.features.loot.resources.types import EquipmentEntry, ResourceEntry
from src.backend.features.monsters.resources import get_starter_family_ids


@pytest.mark.unit
def test_starter_monster_families_have_explicit_loot_profiles() -> None:
    missing = [family_id for family_id in get_starter_family_ids() if family_id not in LOOT_PROFILES]

    assert missing == []


@pytest.mark.unit
def test_all_loot_equipment_entries_use_existing_item_bases() -> None:
    invalid_equipment = []
    for profile_id, profile in LOOT_PROFILES.items():
        for role, role_profile in profile.roles.items():
            for entry in role_profile.drop:
                if isinstance(entry, EquipmentEntry) and get_base_by_id(entry.base_id) is None:
                    invalid_equipment.append((profile_id, role, entry.base_id))

    assert invalid_equipment == []


@pytest.mark.unit
@pytest.mark.parametrize("family_id", ["bandit_gang", "goblin_tribe"])
def test_humanoid_loot_profiles_drop_valid_equipment_and_tier_zero_junk(family_id: str) -> None:
    profile = LOOT_PROFILES[family_id]
    invalid_equipment = []
    missing_equipment_roles = []
    missing_junk_roles = []

    for role, role_profile in profile.roles.items():
        equipment = [entry for entry in role_profile.drop if isinstance(entry, EquipmentEntry)]
        junk = [
            entry
            for entry in role_profile.drop
            if isinstance(entry, ResourceEntry) and resolve_resource(entry.profile, entry.fixed_tier or 0)
        ]
        if not equipment:
            missing_equipment_roles.append(role)
        if not any(isinstance(entry, ResourceEntry) and entry.fixed_tier == 0 for entry in junk):
            missing_junk_roles.append(role)
        for entry in equipment:
            if get_base_by_id(entry.base_id) is None:
                invalid_equipment.append((role, entry.base_id))

    assert missing_equipment_roles == []
    assert missing_junk_roles == []
    assert invalid_equipment == []
