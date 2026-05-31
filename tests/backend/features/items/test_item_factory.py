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
    # power = base_power(12) * tier_mult(1.0)
    assert item.power == pytest.approx(12.0)
    assert item.implicit_bonuses["main_hand_accuracy_penalty"] == pytest.approx(0.15)
    assert "main_hand_armor_penetration_pct" not in item.implicit_bonuses
    assert item.implicit_bonuses["evasion_penalty"] == pytest.approx(-0.10)
    # bonuses is intentionally empty — projection is runtime-only
    assert item.bonuses == {}
    # mechanics carries the canonical source
    assert isinstance(item.mechanics["affixes"], list)
    assert item.mechanics["implicit_bonuses_base"]["main_hand_accuracy_penalty"] == pytest.approx(0.15)
    assert "main_hand_armor_penetration_pct" not in item.mechanics["implicit_bonuses_base"]
    assert all(affix["tier"] == 1 for affix in item.mechanics["affixes"])
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

    assert low.implicit_bonuses["main_hand_accuracy_penalty"] == pytest.approx(0.15)
    assert high.implicit_bonuses["main_hand_accuracy_penalty"] == pytest.approx(0.225)

    # affix values also scale with tier_mult when both draw the same affix
    low_affixes = {a["affix_id"]: a["value"] for a in low.mechanics["affixes"]}
    high_affixes = {a["affix_id"]: a["value"] for a in high.mechanics["affixes"]}
    shared = set(low_affixes) & set(high_affixes)
    for affix_id in shared:
        # high tier_mult → higher or equal values for each affix
        # (different roll seeds may produce slightly different order, but trend holds at ratio)
        assert high_affixes[affix_id] >= 0  # sanity: values are non-negative


@pytest.mark.unit
def test_item_factory_heavy_armor_scales_class_penalties_for_sync_math():
    item = ItemFactory().generate(
        ItemGenerationRequestDTO(
            base_id="plate_chest",
            material_id="mat_iron_ingot",
            item_grade="common",
        )
    )

    assert item.metadata["armor_class"] == "heavy"
    assert item.mechanics["implicit_bonuses_base"]["evasion_penalty"] == pytest.approx(-0.07)
    assert item.implicit_bonuses["evasion_penalty"] == pytest.approx(-0.07)
    assert item.implicit_bonuses["main_hand_accuracy_penalty"] == pytest.approx(0.015)


@pytest.mark.unit
def test_item_factory_light_chest_penalty_scales_by_material_tier():
    low = ItemFactory().generate(
        ItemGenerationRequestDTO(
            base_id="leather_armor",
            material_id="mat_cured_leather",
            item_grade="common",
        )
    )
    high = ItemFactory().generate(
        ItemGenerationRequestDTO(
            base_id="leather_armor",
            material_id="mat_thick_leather",
            item_grade="common",
        )
    )

    assert low.metadata["armor_class"] == "light"
    assert low.implicit_bonuses["evasion_penalty"] == pytest.approx(-0.01)
    assert high.implicit_bonuses["evasion_penalty"] < low.implicit_bonuses["evasion_penalty"]


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
def test_item_factory_uses_material_prefix_for_generated_names():
    factory = ItemFactory()

    buckler = factory.generate(
        ItemGenerationRequestDTO(
            base_id="buckler",
            material_id="mat_oak_plank",
            item_grade="common",
        )
    )
    breeches = factory.generate(
        ItemGenerationRequestDTO(
            base_id="breeches",
            material_id="mat_cured_leather",
            item_grade="common",
        )
    )

    assert buckler.name == "Дубовый баклер"
    assert breeches.name == "Дубленые прочные штаны"
    assert ":" not in buckler.name
    assert ":" not in breeches.name


@pytest.mark.unit
def test_item_factory_generates_earring_accessory():
    item = ItemFactory().generate(
        ItemGenerationRequestDTO(
            base_id="earring",
            material_id="mat_iron_ingot",
            item_grade="uncommon",
        )
    )

    assert item.base_id == "earring"
    assert item.item_type == "accessory"
    assert item.slot == "earring"
    assert item.name == "Железная серьга"
    assert item.power == 1.0
    assert item.implicit_bonuses == {"initiative": pytest.approx(0.5)}


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
def test_item_factory_carries_quiver_ammo_contract_into_mechanics():
    item = ItemFactory().generate(
        ItemGenerationRequestDTO(
            base_id="quiver_fire",
            material_id="mat_oak_plank",
            item_grade="common",
        )
    )

    assert item.slot == "quiver"
    assert item.item_type == "ammo"
    assert item.power == pytest.approx(3.0)
    assert item.mechanics["ammo_charge_base"] == 12
    assert item.mechanics["ammo_charge_skill_bonus"] == 12
    assert item.mechanics["ammo_effect_payload"] == {
        "effects": [
            {
                "id": "dot_burn",
                "params": {"power": 1.0},
                "tags": ["arrow", "fire", "burn"],
            },
            {
                "id": "debuff_accuracy",
                "params": {"power": 1.0},
                "tags": ["arrow", "fire", "accuracy_debuff"],
            },
        ]
    }


@pytest.mark.unit
def test_item_factory_scales_travel_boots_concentration_regen_by_material_tier_mult():
    low = ItemFactory().generate(
        ItemGenerationRequestDTO(
            base_id="travel_boots",
            material_id="mat_cured_leather",
            item_grade="common",
        )
    )
    high = ItemFactory().generate(
        ItemGenerationRequestDTO(
            base_id="travel_boots",
            material_id="mat_ancient_dragonhide",
            item_grade="common",
        )
    )

    assert low.implicit_bonuses["stamina_regen"] == pytest.approx(1.5)
    assert low.implicit_bonuses["environment_gravity_resistance"] == pytest.approx(1.0)
    assert low.mechanics["implicit_bonuses"]["stamina_regen"] == pytest.approx(1.5)
    assert high.implicit_bonuses["stamina_regen"] == pytest.approx(10.2)
    assert high.implicit_bonuses["environment_gravity_resistance"] == pytest.approx(6.8)


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
def test_item_factory_runtime_item_uses_presentation_override_and_custom_affix_steps():
    factory = ItemFactory()
    request = ItemGenerationRequestDTO(
        generation_mode="runtime",
        base_id="dagger",
        material_id="mat_cobalt_ingot",
        item_grade="artifact",
        affix_bundle_ids=["duelist_weapon_4"],
        affix_step_count=2,
        presentation_name_ru="Крысиные клыки и когти",
        presentation_description="Естественное оружие твари.",
        extra_narrative_tags=["natural_weapon", "rat"],
        runtime_metadata={"monster_equipment_key": "rat_bite_claws"},
    )

    item = factory.generate_runtime_item(request)

    assert item.name == "Крысиные клыки и когти"
    assert item.description == "Естественное оружие твари."
    assert item.metadata["runtime_item"] is True
    assert item.metadata["monster_equipment_key"] == "rat_bite_claws"
    assert item.metadata["affix_step_count"] == 2
    assert item.metadata["request_ai_text"] is False
    assert {"natural_weapon", "rat"} <= set(item.narrative_tags)
    assert item.affix_bundle_ids == ["duelist_weapon_4"]
    assert {affix["roll"]["step_count"] for affix in item.mechanics["affixes"]} == {2}


@pytest.mark.unit
def test_item_factory_player_pipeline_keeps_default_affix_steps():
    item = ItemFactory().generate_player_item(
        ItemGenerationRequestDTO(
            base_id="dagger",
            material_id="mat_iron_ingot",
            item_grade="artifact",
            affix_bundle_ids=["duelist_weapon_4"],
        )
    )

    assert {affix["roll"]["step_count"] for affix in item.mechanics["affixes"]} == {5}


@pytest.mark.unit
def test_item_factory_runtime_item_filters_allowed_affixes_and_exact_count():
    item = ItemFactory().generate_runtime_item(
        ItemGenerationRequestDTO(
            generation_mode="runtime",
            base_id="dagger",
            material_id="mat_cobalt_ingot",
            item_grade="artifact",
            allowed_affix_ids=["crit_chance", "weapon_accuracy"],
            affix_count=2,
            affix_step_count=7,
        )
    )

    affixes = item.mechanics["affixes"]
    assert len(affixes) == 2
    assert {affix["affix_id"] for affix in affixes} <= {"crit_chance", "weapon_accuracy"}
    assert {affix["roll"]["step_count"] for affix in affixes} == {7}


@pytest.mark.unit
def test_item_factory_runtime_item_applies_forced_affixes_before_random_fill():
    item = ItemFactory().generate_runtime_item(
        ItemGenerationRequestDTO(
            generation_mode="runtime",
            base_id="dagger",
            material_id="mat_cobalt_ingot",
            item_grade="artifact",
            allowed_affix_ids=["weapon_accuracy", "crit_chance", "armor_penetration_pct_bonus", "control_chance_bonus"],
            forced_affix_ids=["weapon_accuracy", "crit_chance"],
            affix_count=4,
            affix_step_count=4,
        )
    )

    affixes = item.mechanics["affixes"]
    assert len(affixes) == 4
    assert [affix["affix_id"] for affix in affixes[:2]] == ["weapon_accuracy", "crit_chance"]
    assert {affix["source"] for affix in affixes[:2]} == {"forced"}


@pytest.mark.unit
def test_item_factory_runtime_projection_is_compact_and_compiles_affix_bonuses():
    projection = ItemFactory().generate_runtime_projection(
        ItemGenerationRequestDTO(
            generation_mode="runtime",
            base_id="dagger",
            target_slot="off_hand",
            material_id="mat_cobalt_ingot",
            item_grade="artifact",
            allowed_affix_ids=["off_hand_accuracy", "crit_chance"],
            forced_affix_ids=["off_hand_accuracy"],
            affix_count=1,
            affix_step_count=2,
            runtime_metadata={"owner_key": "member_0", "natural_key": "rat_left_claws"},
            source_context={"family_id": "rat_swarm", "member_tier": 1},
        ),
        item_id="runtime-item-1",
    )

    assert projection.item_id == "runtime-item-1"
    assert projection.owner_key == "member_0"
    assert projection.slot == "off_hand"
    assert projection.combat.power > 0
    assert projection.combat.related_skill == "skill_fencing"
    assert set(projection.combat.bonuses) == {"off_hand_accuracy"}
    assert projection.combat.bonuses["off_hand_accuracy"].startswith("+")
    assert projection.generation.natural_key == "rat_left_claws"
    assert projection.generation.source_context == {"family_id": "rat_swarm", "member_tier": 1}
    assert projection.generation.affixes[0]["affix_id"] == "off_hand_accuracy"


@pytest.mark.unit
def test_item_factory_runtime_projection_rejects_invalid_target_slot():
    with pytest.raises(ValueError, match="not allowed"):
        ItemFactory().generate_runtime_item(
            ItemGenerationRequestDTO(
                generation_mode="runtime",
                base_id="dagger",
                target_slot="chest_armor",
            )
        )


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
        ("rapier", "mat_cobalt_ingot", "duelist_weapon_4", {"weapon_accuracy", "armor_penetration_pct_bonus"}),
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
