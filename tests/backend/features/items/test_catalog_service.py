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
def test_mvp_armor_catalog_has_exact_three_four_piece_sets():
    catalog = ItemCatalogService.load_default()
    expected_sets = {
        "light": {
            "hood": ("head_armor", 1),
            "leather_armor": ("chest_armor", 2),
            "soft_bracers": ("arms_armor", 1),
            "scout_leggings": ("legs_armor", 1),
        },
        "medium": {
            "leather_cap": ("head_armor", 1),
            "jerkin": ("chest_armor", 4),
            "reinforced_gloves": ("arms_armor", 1),
            "breeches": ("legs_armor", 2),
        },
        "heavy": {
            "helmet": ("head_armor", 2),
            "plate_chest": ("chest_armor", 5),
            "gauntlets": ("arms_armor", 2),
            "greaves": ("legs_armor", 3),
        },
    }
    removed_armor_ids = {
        "robe",
        "sandals",
        "goggles",
        "chainmail",
        "brigandine",
        "boots",
        "scale_mail",
        "sabatons",
    }

    armor_ids = {
        item_id
        for item_id, entry in catalog.entries.items()
        if entry.meta_type == "base" and entry.category == "armor"
    }

    assert armor_ids == {item_id for armor_set in expected_sets.values() for item_id in armor_set}
    assert armor_ids.isdisjoint(removed_armor_ids)
    for armor_class, armor_set in expected_sets.items():
        for item_id, (slot, power) in armor_set.items():
            item = catalog.get_base_item(item_id)
            assert item is not None
            assert item.slot == slot
            assert item.armor_class == armor_class
            assert item.base_power == power


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

    accuracy_penalty_items = []
    missing_skill = []
    for item_id in starting_weapon_ids:
        item = catalog.get_base_item(item_id)
        assert item is not None
        if not item.related_skill:
            missing_skill.append(item_id)
        if "accuracy_penalty" in item.implicit_bonuses:
            accuracy_penalty_items.append(item_id)

    assert missing_skill == []
    assert accuracy_penalty_items == []


@pytest.mark.unit
def test_player_weapons_do_not_carry_base_accuracy_penalty() -> None:
    catalog = ItemCatalogService.load_default()

    offenders = [
        item_id
        for item_id, item in catalog.base_items.items()
        if item.type == "weapon"
        and catalog.entries[item_id].category != "monster_equipment"
        and "accuracy_penalty" in item.implicit_bonuses
    ]

    assert offenders == []


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
def test_piercing_fencing_weapons_work_flat_armor_instead_of_bleeding():
    catalog = ItemCatalogService.load_default()

    expected_triggers = {
        "knife": ["crit.weapon_flat_armor_gap_crit"],
        "dagger": ["crit.weapon_flat_armor_gap_crit"],
        "stiletto": ["crit.weapon_flat_armor_bypass_crit"],
        "katar": ["crit.weapon_flat_armor_bypass_crit"],
    }

    for item_id, triggers in expected_triggers.items():
        item = catalog.get_base_item(item_id)
        assert item is not None
        assert item.triggers == triggers
        assert all("bleed" not in trigger for trigger in item.triggers)


@pytest.mark.unit
def test_weapon_base_crit_chance_is_balanced_for_skill_multiplier_model():
    catalog = ItemCatalogService.load_default()

    expected_crit = {
        "sling": 0.025,
        "shortbow": 0.035,
        "knife": 0.06,
        "dagger": 0.07,
        "stiletto": 0.075,
        "rapier": 0.08,
        "main_gauche": 0.05,
        "katar": 0.085,
        "hatchet": 0.03,
        "battle_axe": 0.04,
        "mace": 0.025,
        "warhammer": 0.035,
        "flail": 0.04,
        "spear": 0.035,
        "pike": 0.04,
        "halberd": 0.04,
        "quarterstaff": 0.02,
        "trident": 0.035,
        "sword": 0.045,
        "longsword": 0.05,
        "greatsword": 0.04,
        "katana": 0.10,
        "scimitar": 0.07,
    }

    for item_id, expected in expected_crit.items():
        item = catalog.get_base_item(item_id)
        assert item is not None
        assert item.implicit_bonuses["physical_crit_chance"] == pytest.approx(expected)


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
def test_starting_parry_rewards_reach_cap_only_near_full_parrying_skill():
    catalog = ItemCatalogService.load_default()

    def base_parry(*item_ids: str) -> float:
        # Scenario rewards are generated at rarity tier 0, so starter ingot/wood items use tier_mult=0.8.
        return sum(float(catalog.get_base_item(item_id).implicit_bonuses.get("parry_chance", 0.0)) for item_id in item_ids) * 0.8

    def final_parry(raw_base: float, skill: float) -> float:
        return min(raw_base * (1.0 + 4.0 * skill), 0.50)

    parry_builds = {
        "dagger_main_gauche": base_parry("dagger", "main_gauche"),
        "sword_buckler": base_parry("sword", "buckler"),
    }

    for raw_base in parry_builds.values():
        assert final_parry(raw_base, 0.25) <= 0.25
        assert final_parry(raw_base, 1.0) == pytest.approx(0.50)

    assert final_parry(base_parry("dagger", "dagger"), 1.0) < 0.30


@pytest.mark.unit
def test_primary_offhand_parry_weapons_trade_offense_for_defense():
    catalog = ItemCatalogService.load_default()
    main_gauche = catalog.get_base_item("main_gauche")
    rapier = catalog.get_base_item("rapier")
    dagger = catalog.get_base_item("dagger")
    stiletto = catalog.get_base_item("stiletto")

    assert main_gauche is not None
    assert rapier is not None
    assert dagger is not None
    assert stiletto is not None

    assert main_gauche.slot == "off_hand"
    assert "main_hand" in main_gauche.extra_slots
    assert main_gauche.implicit_bonuses["parry_chance"] >= rapier.implicit_bonuses["parry_chance"] * 2
    assert main_gauche.base_power < dagger.base_power
    assert main_gauche.base_power < stiletto.base_power
    assert main_gauche.implicit_bonuses["physical_crit_chance"] < dagger.implicit_bonuses["physical_crit_chance"]
    assert main_gauche.implicit_bonuses["physical_crit_chance"] < stiletto.implicit_bonuses["physical_crit_chance"]


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
