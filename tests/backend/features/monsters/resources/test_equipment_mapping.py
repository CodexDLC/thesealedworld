import pytest

from src.backend.features.items.services.catalog_service import ItemCatalogService
from src.backend.features.monsters.resources.equipment_mapping import NATURAL_EQUIPMENT_MAPPINGS


@pytest.mark.unit
def test_natural_equipment_mappings_reference_existing_base_items_and_slots() -> None:
    catalog = ItemCatalogService.load_default()
    missing: list[str] = []
    invalid_slots: list[tuple[str, str, str]] = []
    for natural_key, mapping in NATURAL_EQUIPMENT_MAPPINGS.items():
        base = catalog.get_base_item(mapping.base_id)
        if base is None:
            missing.append(natural_key)
            continue
        valid_slots = {base.slot, *base.extra_slots}
        if mapping.default_slot not in valid_slots:
            invalid_slots.append((natural_key, mapping.base_id, mapping.default_slot))

    assert missing == []
    assert invalid_slots == []


@pytest.mark.unit
def test_natural_weapon_mappings_resolve_to_real_weapon_skill_contracts() -> None:
    catalog = ItemCatalogService.load_default()
    problems: list[tuple[str, str, str | None, str | None]] = []
    for natural_key, mapping in NATURAL_EQUIPMENT_MAPPINGS.items():
        if mapping.item_kind != "weapon":
            continue
        base = catalog.get_base_item(mapping.base_id)
        if base is None:
            continue
        if base.type != "weapon" or base.related_skill == "skill_unarmed":
            problems.append((natural_key, mapping.base_id, base.type, base.related_skill))

    assert problems == []


@pytest.mark.unit
def test_natural_equipment_mappings_cover_mvp_beast_families() -> None:
    assert {"rat_bite_claws", "rat_light_hide", "wolf_bite_claws", "wolf_hide"} <= set(
        NATURAL_EQUIPMENT_MAPPINGS
    )
