import pytest

from src.backend.core.calculators.stats_waterfall_calculator import StatsWaterfallCalculator
from src.backend.features.items.resources.affix_balance import GLOBAL_AFFIX_STEPS
from src.backend.features.items.resources.affixes.catalog import AFFIX_CATALOG, BUNDLE_CATALOG
from src.backend.features.items.resources.affixes.pools import (
    AFFIX_POOLS_BY_ITEM_TYPE,
    AFFIX_POOLS_BY_SLOT,
    AFFIX_POOLS_BY_TAG,
)
from src.backend.features.items.resources.modifier_contracts import (
    MODIFIER_CONTRACTS,
    ModifierContractDTO,
    compile_modifier_command,
)
from src.backend.features.items.runtime.item_factory import ItemFactory
from src.shared.enums.item_enums import EquippedSlot


@pytest.mark.unit
def test_modifier_contract_compiler_emits_waterfall_commands():
    assert compile_modifier_command(MODIFIER_CONTRACTS["crit_chance_add"], 0.05) == "+0.05"
    assert compile_modifier_command(MODIFIER_CONTRACTS["crit_chance_add"], -0.05) == "-0.05"

    mult = ModifierContractDTO(
        id="damage_mult_test",
        target_field="damage_mult",
        operation="mult",
        value_kind="percent",
    )
    assert compile_modifier_command(mult, 0.10) == "*1.1"
    assert compile_modifier_command(mult, -0.10) == "*0.9"

    set_contract = ModifierContractDTO(
        id="crit_cap_set_test",
        target_field="main_hand_crit_cap",
        operation="set",
        value_kind="percent",
    )
    assert compile_modifier_command(set_contract, 0.35) == "=0.35"


@pytest.mark.unit
def test_compiled_modifier_commands_are_accepted_by_waterfall():
    commands = [
        compile_modifier_command(MODIFIER_CONTRACTS["crit_chance_add"], 0.05),
        compile_modifier_command(
            ModifierContractDTO("test_mult", "crit_chance", "mult", "percent"),
            0.10,
        ),
    ]

    value, formula = StatsWaterfallCalculator.evaluate_sources(commands, base_value=0.10)

    assert value == pytest.approx(0.165)
    assert formula == "(0.1 + 0.05) * 1.1"


@pytest.mark.unit
def test_affix_catalog_references_existing_modifier_contracts():
    missing = [
        (affix_id, entry.technical.modifier_id)
        for affix_id, entry in AFFIX_CATALOG.items()
        if entry.technical.modifier_id not in MODIFIER_CONTRACTS
    ]

    assert missing == []


@pytest.mark.unit
def test_affix_pools_reference_existing_affixes_and_real_slots():
    unknown_by_type = [
        (pool_id, affix_id)
        for pool_id, affix_ids in AFFIX_POOLS_BY_ITEM_TYPE.items()
        for affix_id in affix_ids
        if affix_id not in AFFIX_CATALOG
    ]
    unknown_by_slot = [
        (slot_id, affix_id)
        for slot_id, affix_ids in AFFIX_POOLS_BY_SLOT.items()
        for affix_id in affix_ids
        if affix_id not in AFFIX_CATALOG
    ]
    unknown_by_tag = [
        (tag_id, affix_id)
        for tag_id, affix_ids in AFFIX_POOLS_BY_TAG.items()
        for affix_id in affix_ids
        if affix_id not in AFFIX_CATALOG
    ]
    equipment_slots = {slot.value for slot in EquippedSlot}
    invalid_slot_keys = [slot_id for slot_id in AFFIX_POOLS_BY_SLOT if slot_id not in equipment_slots]

    assert unknown_by_type == []
    assert unknown_by_slot == []
    assert unknown_by_tag == []
    assert invalid_slot_keys == []


@pytest.mark.unit
def test_type_specific_bundles_are_possible_from_item_type_pools():
    missing_from_type_pool = []
    shield_required_outside_shield = []
    for bundle in BUNDLE_CATALOG.values():
        for item_type in bundle.allowed_item_types:
            type_pool = set(AFFIX_POOLS_BY_ITEM_TYPE.get(item_type, []))
            for affix_id in bundle.affix_ids:
                if affix_id not in type_pool:
                    missing_from_type_pool.append((bundle.id, item_type, affix_id))
                entry = AFFIX_CATALOG[affix_id]
                if "shield" in entry.technical.required_item_tags and item_type != "shield":
                    shield_required_outside_shield.append((bundle.id, item_type, affix_id))

    assert missing_from_type_pool == []
    assert shield_required_outside_shield == []


@pytest.mark.unit
def test_affix_base_values_stay_in_mvp_ranges_for_tier_one_materials():
    max_value_by_kind = {
        "probability": 0.025,
        "flat_decimal": 3.0,
        "flat_int": 20.0,
        "multiplier_delta": 0.025,
    }
    offenders = []

    for affix_id, entry in AFFIX_CATALOG.items():
        max_roll = entry.technical.base_value * GLOBAL_AFFIX_STEPS * (1.0 + entry.technical.roll_profile.step_spread)
        allowed = max_value_by_kind[entry.technical.value_kind]
        if max_roll > allowed:
            offenders.append((affix_id, entry.technical.value_kind, round(max_roll, 4), allowed))

    assert offenders == []


@pytest.mark.unit
def test_magic_affixes_are_catalog_ready_but_not_in_item_generation_pools():
    reserved_magic_affixes = {
        "magic_damage_bonus",
        "magic_penetration_bonus",
        "fire_damage_bonus",
        "fire_resistance_bonus",
        "arcane_resistance_bonus",
        "vampiric_power_bonus",
        "vampiric_trigger_chance_bonus",
    }
    pooled_affixes = (
        set().union(*AFFIX_POOLS_BY_ITEM_TYPE.values())
        | set().union(*AFFIX_POOLS_BY_SLOT.values())
        | set().union(*AFFIX_POOLS_BY_TAG.values())
    )

    assert reserved_magic_affixes <= set(AFFIX_CATALOG)
    assert reserved_magic_affixes.isdisjoint(pooled_affixes)


@pytest.mark.unit
def test_affix_pools_preserve_first_pass_build_identities():
    weapon_pool = set(
        ItemFactory._pool_for_item(
            "weapon",
            "two_hand",
            ["hammer", "macing", "heavy"],
            item_tier=3,
            already_chosen=set(),
        )
    )
    heavy_armor_pool = set(
        ItemFactory._pool_for_item(
            "armor",
            "chest_armor",
            ["plate", "heavy", "metal"],
            item_tier=3,
            already_chosen=set(),
        )
    )
    light_armor_pool = set(
        ItemFactory._pool_for_item(
            "armor",
            "chest_armor",
            ["robe", "light", "cloth"],
            item_tier=3,
            already_chosen=set(),
        )
    )
    belt_pool = set(
        ItemFactory._pool_for_item(
            "belt",
            "belt_accessory",
            ["belt", "accessory", "waist"],
            item_tier=3,
            already_chosen=set(),
        )
    )
    shield_pool = set(
        ItemFactory._pool_for_item(
            "shield",
            "off_hand",
            ["shield", "metal"],
            item_tier=3,
            already_chosen=set(),
        )
    )

    assert {"hp_bonus", "en_bonus"}.isdisjoint(weapon_pool)
    assert {"travel_speed", "scouting_bonus", "pathfinding_bonus"}.isdisjoint(heavy_armor_pool)
    assert "thorns_damage_bonus" in heavy_armor_pool
    assert "shield_guard_power_bonus" in shield_pool
    assert "armor_flat" not in light_armor_pool
    assert {"evasion_bonus", "hp_regen_bonus"} <= light_armor_pool
    assert {"resource_find_chance", "crafting_speed", "travel_speed"} <= belt_pool
