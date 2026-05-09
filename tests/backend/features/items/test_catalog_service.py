import pytest

from src.backend.features.combat.dto.trigger_rules import TriggerRulesFlagsDTO
from src.backend.features.items.services.catalog_service import ItemCatalogService

WEAPON_DIRECTIONS_EXCEPT_ARCHERY = {
    "skill_swords": {"sword", "longsword", "greatsword", "katana", "scimitar"},
    "skill_macing": {"hatchet", "battle_axe", "mace", "warhammer", "flail"},
    "skill_polearms": {"spear", "pike", "halberd", "quarterstaff", "trident"},
    "skill_fencing": {"knife", "dagger", "stiletto", "rapier", "main_gauche", "katar"},
}

DAGGERLIKE_DUAL_SLOT_WEAPONS = {"knife", "dagger", "stiletto", "main_gauche", "katar"}
CAPACITY_KEYS = {"inventory_cell_capacity", "inventory_slot_capacity", "inventory_slots", "quick_slot_capacity"}
ATTRIBUTE_KEYS = {"strength", "agility", "intelligence", "constitution", "perception", "willpower", "charisma"}


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
    assert catalog.get_affix_entry("weapon_accuracy")
    assert catalog.get_affix_bundle("duelist_weapon_4")
    assert catalog.get_rarity(0).enum_key == "shared"


@pytest.mark.unit
def test_item_catalog_exposes_new_affix_bundle_lookup():
    catalog = ItemCatalogService.load_default()

    bundle = catalog.get_affix_bundle("bulwark_shield_4")
    assert bundle is not None
    assert bundle.affix_ids == ("armor_flat", "block_bonus", "shield_guard_power_bonus", "physical_resistance_bonus")


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


@pytest.mark.unit
def test_weapon_directions_except_archery_have_core_base_items():
    catalog = ItemCatalogService.load_default()

    for skill_key, item_ids in WEAPON_DIRECTIONS_EXCEPT_ARCHERY.items():
        loaded = {item_id: catalog.get_base_item(item_id) for item_id in item_ids}
        assert [item_id for item_id, item in loaded.items() if item is None] == []
        assert {item.related_skill for item in loaded.values() if item is not None} == {skill_key}
        assert sum(1 for item in loaded.values() if item is not None and item.triggers) >= 3


@pytest.mark.unit
def test_daggerlike_fencing_weapons_support_main_and_off_hand():
    catalog = ItemCatalogService.load_default()

    for item_id in DAGGERLIKE_DUAL_SLOT_WEAPONS:
        item = catalog.get_base_item(item_id)
        assert item is not None
        assert {item.slot, *item.extra_slots} == {"main_hand", "off_hand"}


@pytest.mark.unit
def test_base_item_triggers_reference_runtime_trigger_flags():
    catalog = ItemCatalogService.load_default()
    flags = TriggerRulesFlagsDTO()
    checked_item_ids = {
        item_id
        for item_id, item in catalog.base_items.items()
        if item.type == "weapon" and catalog.entries[item_id].category != "monster_equipment"
    }

    missing = []
    non_weapon_triggers = []
    for item_id in checked_item_ids:
        item = catalog.get_base_item(item_id)
        assert item is not None
        for trigger_id in item.triggers:
            section_name, _, field_name = trigger_id.partition(".")
            section = getattr(flags, section_name, None)
            if not section or not field_name or not hasattr(section, field_name):
                missing.append(f"{item.id}:{trigger_id}")
            if not field_name.startswith("weapon_"):
                non_weapon_triggers.append(f"{item.id}:{trigger_id}")

    assert missing == []
    assert non_weapon_triggers == []


@pytest.mark.unit
def test_player_base_items_do_not_carry_passive_counter_attack_chance():
    catalog = ItemCatalogService.load_default()

    offenders = [
        item_id
        for item_id, item in catalog.base_items.items()
        if catalog.entries[item_id].category != "monster_equipment" and "counter_attack_chance" in item.implicit_bonuses
    ]

    assert offenders == []


@pytest.mark.unit
def test_parry_base_bonus_is_limited_to_weapons_and_parrying_offhand():
    catalog = ItemCatalogService.load_default()

    offenders = []
    for item_id, item in catalog.base_items.items():
        if catalog.entries[item_id].category == "monster_equipment":
            continue
        if "parry_chance" not in item.implicit_bonuses:
            continue
        if item.type == "weapon":
            continue
        if item.slot == "off_hand" and "parry" in item.narrative_tags:
            continue
        offenders.append(item_id)

    assert offenders == []


@pytest.mark.unit
def test_base_attribute_and_capacity_bonuses_stay_in_their_expected_item_types():
    catalog = ItemCatalogService.load_default()

    attribute_offenders = []
    capacity_offenders = []
    for item_id, item in catalog.base_items.items():
        if catalog.entries[item_id].category == "monster_equipment":
            continue
        bonuses = set(item.implicit_bonuses)
        if bonuses & ATTRIBUTE_KEYS and item.type != "accessory":
            attribute_offenders.append(item_id)
        if bonuses & CAPACITY_KEYS and item_id != "belt":
            capacity_offenders.append(item_id)

    assert attribute_offenders == []
    assert capacity_offenders == []
