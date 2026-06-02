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


@pytest.mark.unit
def test_rat_natural_equipment_covers_current_tactical_styles() -> None:
    expected = {
        "rat_offhand_bite": ("dagger", "off_hand", "weapon"),
        "rat_bone_growth": ("buckler", "off_hand", "shield"),
        "rat_spiked_growth": ("shield", "off_hand", "shield"),
        "rat_poison_spit": ("shortbow", "two_hand", "weapon"),
        "rat_poison_glands": ("quiver_training", "quiver", "ammo"),
        "rat_crushing_bite": ("warhammer", "two_hand", "weapon"),
        "rat_plague_gland": ("amulet", "amulet", "accessory"),
    }

    for natural_key, (base_id, slot, item_kind) in expected.items():
        mapping = NATURAL_EQUIPMENT_MAPPINGS[natural_key]

        assert mapping.base_id == base_id
        assert mapping.default_slot == slot
        assert mapping.item_kind == item_kind


@pytest.mark.unit
def test_wolf_natural_equipment_covers_current_pack_styles() -> None:
    expected = {
        "wolf_young_claws": ("knife", "off_hand", "weapon"),
        "wolf_raking_claws": ("katar", "off_hand", "weapon"),
        "wolf_locking_fangs": ("main_gauche", "off_hand", "weapon"),
        "wolf_braced_mane": ("buckler", "off_hand", "shield"),
        "wolf_bone_shoulders": ("shield", "off_hand", "shield"),
        "wolf_pack_mark": ("amulet", "amulet", "accessory"),
    }

    for natural_key, (base_id, slot, item_kind) in expected.items():
        mapping = NATURAL_EQUIPMENT_MAPPINGS[natural_key]

        assert mapping.base_id == base_id
        assert mapping.default_slot == slot
        assert mapping.item_kind == item_kind
