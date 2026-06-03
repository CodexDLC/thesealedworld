import pytest

from src.backend.features.combat.dto.trigger_rules import TriggerRulesFlagsDTO
from src.backend.features.items.resources.affixes.catalog import AFFIX_CATALOG
from src.backend.features.items.resources.affixes.pools import AFFIX_POOLS_BY_SLOT
from src.backend.features.items.resources.modifier_contracts import MODIFIER_CONTRACTS
from src.backend.features.items.services.catalog_service import ItemCatalogService

WEAPON_DIRECTIONS_EXCEPT_ARCHERY = {
    "skill_swords": {"sword", "longsword", "greatsword", "katana", "scimitar", "flamberge"},
    "skill_macing": {"hatchet", "battle_axe", "mace", "warhammer", "flail"},
    "skill_polearms": {"spear", "pike", "halberd", "quarterstaff", "trident"},
    "skill_fencing": {"knife", "dagger", "stiletto", "rapier", "main_gauche", "katar", "kris"},
}
ARCHERY_BOWS = {"shortbow", "longbow", "composite_bow"}
ARCHERY_QUIVERS = {
    "quiver_training",
    "quiver_fire",
    "quiver_poison",
    "quiver_broadhead",
    "quiver_frost",
    "quiver_bodkin",
}

FENCING_DUAL_SLOT_WEAPONS = {"knife", "dagger", "stiletto", "rapier", "main_gauche", "katar", "kris"}
CAPACITY_KEYS = {"inventory_cell_capacity", "inventory_slot_capacity", "inventory_slots", "quick_slot_capacity"}
ATTRIBUTE_KEYS = {"strength", "agility", "intelligence", "constitution", "perception", "willpower", "charisma"}
ARMOR_PENALTY_KEYS = {
    "anti_dodge_chance",
    "evasion_penalty",
    "main_hand_accuracy_penalty",
    "off_hand_accuracy_penalty",
}
WEAPON_PROFILE_KEYS = {
    "evasion_penalty",
    "main_hand_accuracy_penalty",
    "off_hand_accuracy_penalty",
    "parry_chance",
    "physical_crit_chance",
}
OFFHAND_DEFENSE_PROFILE_KEYS = {
    "evasion_penalty",
    "main_hand_accuracy_penalty",
    "off_hand_accuracy_penalty",
    "parry_chance",
    "parry_penalty",
}
GARMENT_ANCHOR_PROFILE_KEYS = {
    "environment_bio_resistance",
    "environment_cold_resistance",
    "environment_gravity_resistance",
    "environment_heat_resistance",
}
BANNED_BASE_WEAPON_ALWAYS_ON_KEYS = {
    "armor_penetration_pct",
    "bleed_damage_bonus",
    "main_hand_armor_penetration_pct",
    "off_hand_armor_penetration_pct",
    "physical_suppression",
    "weapon_armor_penetration_pct",
}


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
            "leather_armor": ("chest_armor", 3),
            "soft_bracers": ("arms_armor", 1),
            "scout_leggings": ("legs_armor", 2),
        },
        "medium": {
            "leather_cap": ("head_armor", 1),
            "jerkin": ("chest_armor", 4),
            "reinforced_gloves": ("arms_armor", 1),
            "breeches": ("legs_armor", 2),
        },
        "heavy": {
            "helmet": ("head_armor", 1),
            "plate_chest": ("chest_armor", 5),
            "gauntlets": ("arms_armor", 1),
            "greaves": ("legs_armor", 2),
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
    assert bundle.affix_ids == (
        "shield_guard_power_bonus",
        "physical_resistance_bonus",
        "control_resistance_bonus",
    )


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
        "flamberge",
        "katana",
        "quarterstaff",
        "shortbow",
        "sword",
        "warhammer",
    }

    missing_accuracy_penalty = []
    missing_skill = []
    for item_id in starting_weapon_ids:
        item = catalog.get_base_item(item_id)
        assert item is not None
        if not item.related_skill:
            missing_skill.append(item_id)
        if "main_hand_accuracy_penalty" not in item.implicit_bonuses:
            missing_accuracy_penalty.append(item_id)

    assert missing_skill == []
    assert missing_accuracy_penalty == []


@pytest.mark.unit
def test_player_weapons_carry_base_main_hand_accuracy_penalty() -> None:
    catalog = ItemCatalogService.load_default()

    offenders = [
        item_id
        for item_id, item in catalog.base_items.items()
        if item.type == "weapon"
        and catalog.entries[item_id].category != "monster_equipment"
        and "main_hand_accuracy_penalty" not in item.implicit_bonuses
    ]

    assert offenders == []


@pytest.mark.unit
def test_player_weapon_implicit_profiles_are_crit_parry_accuracy_and_penalties() -> None:
    catalog = ItemCatalogService.load_default()

    offenders = []
    for item_id, item in catalog.base_items.items():
        if item.type != "weapon" or catalog.entries[item_id].category == "monster_equipment":
            continue
        unexpected = sorted(set(item.implicit_bonuses) - WEAPON_PROFILE_KEYS)
        if unexpected:
            offenders.append(f"{item_id}:{','.join(unexpected)}")

    assert offenders == []


@pytest.mark.unit
def test_player_weapons_do_not_carry_always_on_bypass_or_dot_scalers() -> None:
    catalog = ItemCatalogService.load_default()

    offenders = []
    for item_id, item in catalog.base_items.items():
        if item.type != "weapon" or catalog.entries[item_id].category == "monster_equipment":
            continue
        banned = sorted(set(item.implicit_bonuses) & BANNED_BASE_WEAPON_ALWAYS_ON_KEYS)
        if banned:
            offenders.append(f"{item_id}:{','.join(banned)}")

    assert offenders == []


@pytest.mark.unit
def test_equipped_armor_implicit_bonuses_are_only_penalties() -> None:
    catalog = ItemCatalogService.load_default()

    offenders = []
    for item_id, item in catalog.base_items.items():
        if catalog.entries[item_id].category != "armor":
            continue
        unexpected = sorted(set(item.implicit_bonuses) - ARMOR_PENALTY_KEYS)
        if unexpected:
            offenders.append(f"{item_id}:{','.join(unexpected)}")

    assert offenders == []


@pytest.mark.unit
def test_equipped_armor_does_not_reduce_regeneration_resources() -> None:
    catalog = ItemCatalogService.load_default()

    offenders = [
        item_id
        for item_id, item in catalog.base_items.items()
        if catalog.entries[item_id].category == "armor" and "stamina_regen" in item.implicit_bonuses
    ]

    assert offenders == []


@pytest.mark.unit
def test_heavy_armor_penalty_totals_stay_above_medium_after_tuning() -> None:
    catalog = ItemCatalogService.load_default()
    medium = _armor_penalty_totals(catalog, ("leather_cap", "jerkin", "reinforced_gloves", "breeches"))
    heavy = _armor_penalty_totals(catalog, ("helmet", "plate_chest", "gauntlets", "greaves"))

    assert heavy["evasion_penalty"] < medium["evasion_penalty"]
    assert heavy["main_hand_accuracy_penalty"] > medium["main_hand_accuracy_penalty"]
    assert heavy["off_hand_accuracy_penalty"] > medium["off_hand_accuracy_penalty"]


def _armor_penalty_totals(catalog: ItemCatalogService, item_ids: tuple[str, ...]) -> dict[str, float]:
    totals = {
        "evasion_penalty": 0.0,
        "main_hand_accuracy_penalty": 0.0,
        "off_hand_accuracy_penalty": 0.0,
    }
    for item_id in item_ids:
        item = catalog.get_base_item(item_id)
        assert item is not None
        for key in totals:
            totals[key] += float(item.implicit_bonuses.get(key, 0.0))
    return totals


@pytest.mark.unit
def test_offhand_defense_items_keep_guard_or_parry_but_no_offense_profile() -> None:
    catalog = ItemCatalogService.load_default()
    expected_power = {
        "buckler": 6,
        "shield": 12,
        "kite_shield": 16,
        "tower_shield": 24,
    }

    offenders = []
    for item_id, power in expected_power.items():
        item = catalog.get_base_item(item_id)
        assert item is not None
        assert item.base_power == power
        unexpected = sorted(set(item.implicit_bonuses) - OFFHAND_DEFENSE_PROFILE_KEYS)
        if unexpected:
            offenders.append(f"{item_id}:{','.join(unexpected)}")

    shield = catalog.get_base_item("shield")
    buckler = catalog.get_base_item("buckler")
    assert shield is not None
    assert buckler is not None
    assert shield.base_power > buckler.base_power
    assert shield.implicit_bonuses["evasion_penalty"] <= buckler.implicit_bonuses["evasion_penalty"]
    assert "parry_chance" not in buckler.implicit_bonuses
    assert offenders == []


@pytest.mark.unit
def test_jewelry_power_is_flat_magic_armor_and_implicits_are_slot_profiles() -> None:
    catalog = ItemCatalogService.load_default()
    expected_profiles = {
        "ring": ("ring_1", 1.0, {"mental_resistance"}),
        "amulet": ("amulet", 2.0, {"debuff_avoidance"}),
        "earring": ("earring", 1.0, {"initiative"}),
    }

    for item_id, (slot, power, implicit_keys) in expected_profiles.items():
        item = catalog.get_base_item(item_id)
        assert item is not None
        assert item.type == "accessory"
        assert item.slot == slot
        assert item.base_power == power
        assert set(item.implicit_bonuses) == implicit_keys

        affix_targets = {
            MODIFIER_CONTRACTS[AFFIX_CATALOG[affix_id].technical.modifier_id].target_field
            for affix_id in AFFIX_POOLS_BY_SLOT[item.slot]
        }
        assert implicit_keys.isdisjoint(affix_targets)


@pytest.mark.unit
def test_garment_templates_carry_anchor_environment_implicit_profile() -> None:
    catalog = ItemCatalogService.load_default()

    missing_profile = [
        item_id
        for item_id, item in catalog.base_items.items()
        if item.type == "garment" and not (set(item.implicit_bonuses) & GARMENT_ANCHOR_PROFILE_KEYS)
    ]

    assert missing_profile == []


@pytest.mark.unit
def test_non_warhammer_player_weapons_get_power_offset_for_capped_spread() -> None:
    catalog = ItemCatalogService.load_default()
    expected_power = {
        "shortbow": 8,
        "longbow": 11,
        "composite_bow": 11,
        "knife": 3,
        "dagger": 4,
        "stiletto": 4,
        "rapier": 6,
        "main_gauche": 4,
        "katar": 5,
        "kris": 4,
        "hatchet": 6,
        "battle_axe": 8,
        "mace": 7,
        "warhammer": 12,
        "flail": 7,
        "spear": 8,
        "pike": 10,
        "halberd": 11,
        "quarterstaff": 9,
        "trident": 8,
        "sword": 7,
        "longsword": 8,
        "greatsword": 11,
        "katana": 11,
        "scimitar": 7,
        "flamberge": 11,
    }

    actual_power = {
        item_id: item.base_power
        for item_id, item in catalog.base_items.items()
        if item.type == "weapon" and catalog.entries[item_id].category != "monster_equipment"
    }

    assert actual_power == expected_power


@pytest.mark.unit
def test_archery_catalog_has_only_bows_not_sling() -> None:
    catalog = ItemCatalogService.load_default()

    assert catalog.get_base_item("sling") is None
    assert {item_id for item_id in ARCHERY_BOWS if catalog.get_base_item(item_id)} == ARCHERY_BOWS


@pytest.mark.unit
def test_weapon_directions_except_archery_have_core_base_items():
    catalog = ItemCatalogService.load_default()

    for skill_key, item_ids in WEAPON_DIRECTIONS_EXCEPT_ARCHERY.items():
        loaded = {item_id: catalog.get_base_item(item_id) for item_id in item_ids}
        assert [item_id for item_id, item in loaded.items() if item is None] == []
        assert {item.related_skill for item in loaded.values() if item is not None} == {skill_key}
        assert sum(1 for item in loaded.values() if item is not None and item.triggers) >= 3


@pytest.mark.unit
def test_archery_bows_trade_parry_for_crit_and_ranged_triggers():
    catalog = ItemCatalogService.load_default()
    expected_triggers = {
        "shortbow": ["control.weapon_evasive_shot"],
        "longbow": ["crit.weapon_precision_crit"],
        "composite_bow": ["crit.weapon_piercing_crit"],
    }

    loaded = {item_id: catalog.get_base_item(item_id) for item_id in ARCHERY_BOWS}

    assert [item_id for item_id, item in loaded.items() if item is None] == []
    for item_id, item in loaded.items():
        assert item is not None
        assert item.related_skill == "skill_archery"
        assert item.slot == "two_hand"
        assert "bow" in item.narrative_tags
        assert "parry_chance" not in item.implicit_bonuses
        assert item.implicit_bonuses["physical_crit_chance"] <= 0.05
        assert item.triggers == expected_triggers[item_id]


@pytest.mark.unit
def test_archery_quivers_are_single_ammo_items_scaled_by_material_tier():
    catalog = ItemCatalogService.load_default()

    loaded = {item_id: catalog.get_base_item(item_id) for item_id in ARCHERY_QUIVERS}

    assert [item_id for item_id, item in loaded.items() if item is None] == []
    for item_id, item in loaded.items():
        assert item is not None
        assert not item_id.endswith("_t1")
        assert catalog.entries[item_id].category == "accessory"
        assert item.slot == "quiver"
        assert item.type == "ammo"
        assert item.related_skill == "skill_archery"
        assert item.allowed_materials == ["woods"]
        assert item.base_power == 3
        assert item.implicit_bonuses == {}
        assert item.ammo_charge_base == 12
        assert item.ammo_charge_skill_bonus == 12
        assert {"quiver", "arrows", "archery"}.issubset(set(item.narrative_tags))


@pytest.mark.unit
def test_archery_quiver_payloads_reference_existing_post_calc_effects():
    catalog = ItemCatalogService.load_default()
    expected_effects = {
        "quiver_fire": ["dot_burn", "debuff_accuracy"],
        "quiver_poison": ["dot_poison"],
        "quiver_broadhead": ["dot_bleed", "debuff_armor"],
        "quiver_frost": ["dot_frost", "debuff_evasion"],
        "quiver_bodkin": ["debuff_armor"],
    }

    for item_id, effect_ids in expected_effects.items():
        item = catalog.get_base_item(item_id)
        assert item is not None
        effects = item.ammo_effect_payload.get("effects") or [item.ammo_effect_payload]
        assert [effect["id"] for effect in effects] == effect_ids
        for effect in effects:
            assert effect["params"] == {"power": 1.0}
            assert "arrow" in effect["tags"]

    training = catalog.get_base_item("quiver_training")
    assert training is not None
    assert getattr(training, "ammo_effect_payload", None) is None


@pytest.mark.unit
def test_daggerlike_fencing_weapons_support_main_and_off_hand():
    catalog = ItemCatalogService.load_default()

    for item_id in FENCING_DUAL_SLOT_WEAPONS:
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
        "main_gauche": ["crit.weapon_flat_armor_bypass_crit"],
        "katar": ["crit.weapon_flat_armor_bypass_crit"],
    }

    for item_id, triggers in expected_triggers.items():
        item = catalog.get_base_item(item_id)
        assert item is not None
        assert item.triggers == triggers
        assert all("bleed" not in trigger for trigger in item.triggers)


@pytest.mark.unit
def test_serrated_blades_are_the_only_player_base_bleed_weapons() -> None:
    catalog = ItemCatalogService.load_default()

    bleeding_weapons = {
        item_id
        for item_id, item in catalog.base_items.items()
        if item.type == "weapon"
        and catalog.entries[item_id].category != "monster_equipment"
        and "crit.weapon_serrated_bleed_crit" in item.triggers
    }

    assert bleeding_weapons == {"flamberge", "kris"}


@pytest.mark.unit
def test_weapon_base_crit_chance_is_defined_by_grip_contract():
    catalog = ItemCatalogService.load_default()

    checked = []
    for item_id, item in catalog.base_items.items():
        if item.type != "weapon" or catalog.entries[item_id].category == "monster_equipment":
            continue
        checked.append(item_id)
        max_expected = 0.05 if item.slot == "two_hand" else 0.03
        assert item.implicit_bonuses["physical_crit_chance"] <= max_expected + 1e-9
        if item.slot == "main_hand":
            assert item.implicit_bonuses["physical_crit_chance"] == pytest.approx(0.03)

    assert checked


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
def test_player_base_items_do_not_grant_riposte_triggers_directly():
    catalog = ItemCatalogService.load_default()

    offenders = [
        item_id
        for item_id, item in catalog.base_items.items()
        if catalog.entries[item_id].category != "monster_equipment"
        and "parry.weapon_riposte_on_parry" in item.triggers
    ]

    assert offenders == []


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
        if item.slot == "off_hand" and "parry_weapon" in item.narrative_tags:
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
        "sword_main_gauche": base_parry("sword", "main_gauche"),
    }

    for raw_base in parry_builds.values():
        assert final_parry(raw_base, 0.25) <= 0.25
        assert final_parry(raw_base, 1.0) == pytest.approx(0.50)

    assert final_parry(base_parry("dagger", "dagger"), 1.0) < 0.30


@pytest.mark.unit
def test_parry_fencing_weapons_trade_offense_for_defense_without_fixed_offhand_slot():
    catalog = ItemCatalogService.load_default()
    main_gauche = catalog.get_base_item("main_gauche")
    rapier = catalog.get_base_item("rapier")
    dagger = catalog.get_base_item("dagger")
    stiletto = catalog.get_base_item("stiletto")

    assert main_gauche is not None
    assert rapier is not None
    assert dagger is not None
    assert stiletto is not None

    assert main_gauche.slot == "main_hand"
    assert "off_hand" in main_gauche.extra_slots
    assert main_gauche.implicit_bonuses["parry_chance"] >= rapier.implicit_bonuses["parry_chance"] * 2
    assert main_gauche.base_power == dagger.base_power
    assert main_gauche.base_power == stiletto.base_power


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
