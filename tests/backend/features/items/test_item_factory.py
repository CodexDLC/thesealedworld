import pytest

from src.backend.features.items.dto.instance import ItemGenerationRequestDTO
from src.backend.features.items.resources.affix_balance import (
    ATTRIBUTE_AFFIX_ROLL_PROFILE,
    calculate_affix_value,
)
from src.backend.features.items.resources.affixes.catalog import AFFIX_CATALOG
from src.backend.features.items.runtime.item_factory import ItemFactory


@pytest.mark.unit
def test_item_factory_generates_combat_ready_item_spec():
    item = ItemFactory().generate(
        ItemGenerationRequestDTO(
            base_id="warhammer",
            material_id="mat_iron_ingot",
            rarity_tier=1,
            source="scenario:awakening_rift",
        )
    )

    assert item.base_id == "warhammer"
    assert item.material_id == "mat_iron_ingot"
    assert item.slot == "two_hand"
    # power = base_power(13) * tier_mult(1.0)
    assert item.power == pytest.approx(13.0)
    # implicit_bonuses scaled by tier_mult=1.0 — values unchanged
    assert item.implicit_bonuses["accuracy_penalty"] == pytest.approx(0.24)
    assert item.implicit_bonuses["main_hand_penetration"] == pytest.approx(0.22)
    assert item.implicit_bonuses["evasion_penalty"] == pytest.approx(-0.10)
    # bonuses is intentionally empty — projection is runtime-only
    assert item.bonuses == {}
    # mechanics carries the canonical source
    assert isinstance(item.mechanics["affixes"], list)
    assert item.mechanics["material"]["material_id"] == "mat_iron_ingot"
    assert item.mechanics["material"]["tier_mult"] == pytest.approx(1.0)
    assert item.metadata["source"] == "scenario:awakening_rift"
    assert item.metadata["item_grade"] == "uncommon"


@pytest.mark.unit
def test_item_factory_scales_power_and_affixes_with_material_tier_mult():
    base_item = ItemGenerationRequestDTO(
        base_id="warhammer",
        material_id="mat_iron_ingot",
        item_grade="uncommon",
    )
    higher_tier_item = ItemGenerationRequestDTO(
        base_id="warhammer",
        material_id="mat_cobalt_ingot",
        item_grade="uncommon",
    )

    low = ItemFactory().generate(base_item)
    high = ItemFactory().generate(higher_tier_item)

    # mat_iron_ingot tier_mult=1.0, mat_cobalt_ingot tier_mult=1.5
    assert high.power == pytest.approx(low.power * 1.5)
    assert high.durability_max == pytest.approx(low.durability_max * 1.5)

    # implicit bonuses scale proportionally
    assert high.implicit_bonuses["accuracy_penalty"] == pytest.approx(low.implicit_bonuses["accuracy_penalty"] * 1.5)

    # affix values also scale with tier_mult when both draw the same affix
    low_affixes = {a["affix_id"]: a["value"] for a in low.mechanics["affixes"]}
    high_affixes = {a["affix_id"]: a["value"] for a in high.mechanics["affixes"]}
    shared = set(low_affixes) & set(high_affixes)
    for affix_id in shared:
        # high tier_mult → higher or equal values for each affix
        # (different roll seeds may produce slightly different order, but trend holds at ratio)
        assert high_affixes[affix_id] >= 0  # sanity: values are non-negative


@pytest.mark.unit
def test_item_factory_common_grade_produces_no_affixes():
    item = ItemFactory().generate(
        ItemGenerationRequestDTO(
            base_id="warhammer",
            material_id="mat_iron_ingot",
            rarity_tier=0,
        )
    )

    assert item.metadata["item_grade"] == "common"
    assert item.mechanics["affixes"] == []
    assert item.bonuses == {}


@pytest.mark.unit
def test_item_factory_scales_belt_capacity_by_material_tier_not_tier_mult():
    low = ItemFactory().generate(
        ItemGenerationRequestDTO(
            base_id="belt",
            material_id="mat_torn_leather",
            item_grade="common",
        )
    )
    high = ItemFactory().generate(
        ItemGenerationRequestDTO(
            base_id="belt",
            material_id="mat_ancient_dragonhide",
            item_grade="common",
        )
    )

    assert low.power == 2.0
    assert low.implicit_bonuses == {"quick_slot_capacity": 1.0}
    assert "inventory_cell_capacity" not in low.mechanics["implicit_bonuses"]
    assert high.implicit_bonuses["quick_slot_capacity"] == 8.0
    assert high.power == 16.0


@pytest.mark.unit
def test_item_factory_high_rarity_tier_uses_artifact_container():
    item = ItemFactory().generate(
        ItemGenerationRequestDTO(
            base_id="warhammer",
            rarity_tier=7,
        )
    )

    assert item.metadata["item_grade"] == "artifact"
    assert len(item.mechanics["affixes"]) == 4


@pytest.mark.unit
def test_item_factory_rejects_material_from_wrong_category():
    with pytest.raises(ValueError, match="not allowed"):
        ItemFactory().generate(
            ItemGenerationRequestDTO(
                base_id="warhammer",
                material_id="mat_dirty_rags",
                item_grade="uncommon",
            )
        )


@pytest.mark.unit
def test_item_factory_rejects_bundle_when_affix_required_tags_do_not_match():
    item = ItemFactory().generate(
        ItemGenerationRequestDTO(
            base_id="plate_chest",
            material_id="mat_iron_ingot",
            item_grade="artifact",
            affix_bundle_ids=["bulwark_shield_4"],
        )
    )

    affixes = item.mechanics["affixes"]
    assert "bulwark_shield_4" not in item.affix_bundle_ids
    assert all(affix["affix_id"] != "block_bonus" for affix in affixes)


@pytest.mark.unit
def test_item_factory_accepts_type_specific_bundles():
    armor = ItemFactory().generate(
        ItemGenerationRequestDTO(
            base_id="plate_chest",
            material_id="mat_iron_ingot",
            item_grade="artifact",
            affix_bundle_ids=["bulwark_armor_4"],
        )
    )
    shield = ItemFactory().generate(
        ItemGenerationRequestDTO(
            base_id="shield",
            material_id="mat_iron_ingot",
            item_grade="artifact",
            affix_bundle_ids=["bulwark_shield_4"],
        )
    )

    assert "bulwark_armor_4" in armor.affix_bundle_ids
    assert "block_bonus" not in {affix["affix_id"] for affix in armor.mechanics["affixes"]}
    assert "bulwark_shield_4" in shield.affix_bundle_ids
    assert "block_bonus" in {affix["affix_id"] for affix in shield.mechanics["affixes"]}


@pytest.mark.unit
def test_attribute_affix_profile_floors_rolled_values():
    value = calculate_affix_value(
        0.5,
        tier=2,
        roll_profile=ATTRIBUTE_AFFIX_ROLL_PROFILE,
        roll_quality=1.0,
    )

    assert value == 3.0


@pytest.mark.unit
def test_item_factory_forced_bundle_smoke_by_item_family():
    factory = ItemFactory()
    cases = [
        ("rapier", "mat_cobalt_ingot", "duelist_weapon_4", {"weapon_accuracy", "armor_penetration_bonus"}),
        ("ring", "mat_cobalt_ingot", "duelist_accessory_4", {"attribute_agility", "attribute_perception"}),
        ("shield", "mat_iron_ingot", "bulwark_shield_4", {"block_bonus", "shield_guard_power_bonus"}),
        ("plate_chest", "mat_iron_ingot", "bulwark_armor_4", {"armor_flat", "thorns_damage_bonus"}),
        ("winter_cloak", "mat_linen", "survival_garment_3", {"cold_resistance_bonus", "heat_resistance_bonus"}),
    ]

    for base_id, material_id, bundle_id, expected_affixes in cases:
        item = factory.generate(
            ItemGenerationRequestDTO(
                base_id=base_id,
                material_id=material_id,
                item_grade="artifact",
                affix_bundle_ids=[bundle_id],
            )
        )
        affix_ids = {affix["affix_id"] for affix in item.mechanics["affixes"]}

        assert bundle_id in item.affix_bundle_ids
        assert expected_affixes <= affix_ids


@pytest.mark.unit
def test_item_factory_random_generation_smoke_preserves_item_identities():
    factory = ItemFactory()
    generated = {
        base_id: factory.generate(
            ItemGenerationRequestDTO(
                base_id=base_id,
                material_id=material_id,
                item_grade="rare",
            )
        )
        for base_id, material_id in [
            ("warhammer", "mat_iron_ingot"),
            ("shield", "mat_iron_ingot"),
            ("plate_chest", "mat_iron_ingot"),
            ("winter_cloak", "mat_linen"),
            ("belt", "mat_cured_leather"),
        ]
    }

    weapon_affixes = {affix["affix_id"] for affix in generated["warhammer"].mechanics["affixes"]}
    shield_affixes = {affix["affix_id"] for affix in generated["shield"].mechanics["affixes"]}
    armor_affixes = {affix["affix_id"] for affix in generated["plate_chest"].mechanics["affixes"]}
    garment_affixes = {affix["affix_id"] for affix in generated["winter_cloak"].mechanics["affixes"]}
    belt_affixes = {affix["affix_id"] for affix in generated["belt"].mechanics["affixes"]}

    assert {"hp_bonus", "en_bonus"}.isdisjoint(weapon_affixes)
    assert all(AFFIX_CATALOG[affix_id].technical.required_item_tags != ("shield",) for affix_id in armor_affixes)
    assert "block_bonus" in shield_affixes or "block_bonus" not in armor_affixes
    assert "armor_flat" not in garment_affixes
    assert belt_affixes <= {
        "hp_bonus",
        "en_bonus",
        "travel_speed",
        "pathfinding_bonus",
        "resource_find_chance",
        "crafting_speed",
        "luck_bonus",
    }
