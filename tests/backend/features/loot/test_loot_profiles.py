from __future__ import annotations

import pytest

from src.backend.features.items.resources import get_base_by_id
from src.backend.features.loot.resources.equipment_pool import merged_pool
from src.backend.features.loot.resources.profiles import LOOT_PROFILES
from src.backend.features.loot.resources.resolver import resolve_resource
from src.backend.features.loot.resources.types import ResourceEntry
from src.backend.features.monsters.resources import get_starter_family_ids


@pytest.mark.unit
def test_starter_monster_families_have_explicit_loot_profiles() -> None:
    missing = [family_id for family_id in get_starter_family_ids() if family_id not in LOOT_PROFILES]

    assert missing == []


@pytest.mark.unit
def test_all_loot_equipment_entries_use_existing_item_bases() -> None:
    invalid_equipment = []
    for profile_id, profile in LOOT_PROFILES.items():
        if profile.equipment is None:
            continue
        for base_id in merged_pool(profile.equipment.enabled_subcategories):
            if get_base_by_id(base_id) is None:
                invalid_equipment.append((profile_id, base_id))

    assert invalid_equipment == []


@pytest.mark.unit
@pytest.mark.parametrize("family_id", ["bandit_gang", "goblin_tribe"])
def test_humanoid_loot_profiles_drop_valid_equipment_and_tier_zero_junk(family_id: str) -> None:
    profile = LOOT_PROFILES[family_id]
    missing_junk_roles = []

    assert profile.equipment is not None
    allowed_equipment = merged_pool(profile.equipment.enabled_subcategories)
    assert allowed_equipment != []
    assert all(get_base_by_id(base_id) is not None for base_id in allowed_equipment)

    for role, role_profile in profile.roles.items():
        junk = [
            entry
            for entry in role_profile.drop
            if isinstance(entry, ResourceEntry) and resolve_resource(entry.profile, entry.fixed_tier or 0)
        ]
        if not any(isinstance(entry, ResourceEntry) and entry.fixed_tier == 0 for entry in junk):
            missing_junk_roles.append(role)

    assert missing_junk_roles == []


@pytest.mark.unit
def test_all_loot_resource_entries_use_existing_items() -> None:
    from src.backend.features.items.resources import ITEM_REGISTRY

    invalid_resources = []
    for profile_id, profile in LOOT_PROFILES.items():
        for role, role_profile in profile.roles.items():
            entries = list(role_profile.drop) + list(role_profile.salvage) + list(role_profile.spoil)
            for entry in entries:
                if isinstance(entry, ResourceEntry):
                    # Check all possible tiers that a resource could resolve to (0 to 7)
                    tiers_to_check = [entry.fixed_tier] if entry.fixed_tier is not None else range(8)
                    for t in tiers_to_check:
                        resolved_id = resolve_resource(entry.profile, t)
                        if resolved_id not in ITEM_REGISTRY:
                            invalid_resources.append((profile_id, role, entry.profile, t, resolved_id))

    assert invalid_resources == []
