import pytest

from src.backend.features.items.services.catalog_service import ItemCatalogService


@pytest.mark.unit
def test_item_catalog_loads_structured_base_resources_through_pydantic():
    catalog = ItemCatalogService.load_default()

    assert catalog.get_base_item("sword")
    assert catalog.get_base_item("warhammer")
    assert catalog.get_base_item("quarterstaff")
    assert catalog.get_base_item("plate_chest")
    assert catalog.get_base_item("belt")
    assert catalog.get_material("mat_iron_ingot")
    assert catalog.get_raw_resource("currency_dust")
    assert catalog.get_affix_bundle("soldier")
    assert catalog.get_affix_effect("phys_dmg_flat")
    assert catalog.get_rarity(0).enum_key == "shared"


@pytest.mark.unit
def test_item_catalog_builds_reverse_bundle_lookup():
    catalog = ItemCatalogService.load_default()

    bundle = catalog.ingredient_to_bundle["essence_iron_will"]
    assert bundle.id == "soldier"


@pytest.mark.unit
def test_item_catalog_exposes_public_text_projection():
    catalog = ItemCatalogService.load_default()

    public_text = catalog.all_public_text()

    assert public_text["battle_axe"]["title"] == "Боевой топор"
    assert public_text["battle_axe"]["description"]
    assert public_text["battle_axe"]["type"] == "base"
    assert public_text["battle_axe"]["category"] == "weapon"
    assert "base_power" not in public_text["battle_axe"]


@pytest.mark.unit
def test_base_item_catalog_has_public_descriptions_for_all_templates():
    catalog = ItemCatalogService.load_default()

    public_text = catalog.all_public_text()
    missing = [
        item_id
        for item_id, entry in catalog.entries.items()
        if entry.meta_type == "base" and str(public_text[item_id]["description"]).startswith("DATA_MISSING")
    ]

    assert missing == []


@pytest.mark.unit
def test_starting_weapons_match_combat_snapshot_contract():
    catalog = ItemCatalogService.load_default()
    starting_weapon_ids = {
        "battle_axe",
        "dagger",
        "katana",
        "quarterstaff",
        "shortbow",
        "sword",
        "warhammer",
    }

    missing_penalty = []
    missing_skill = []
    for item_id in starting_weapon_ids:
        item = catalog.get_base_item(item_id)
        assert item is not None
        if not item.related_skill:
            missing_skill.append(item_id)
        if "accuracy_penalty" not in item.implicit_bonuses:
            missing_penalty.append(item_id)

    assert missing_skill == []
    assert missing_penalty == []
