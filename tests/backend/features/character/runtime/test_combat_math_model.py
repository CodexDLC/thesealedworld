import pytest

from src.backend.core.calculators.stats_waterfall_calculator import StatsWaterfallCalculator
from src.backend.features.character.runtime import CharacterCombatMathModelBuilder
from src.backend.features.character.runtime.combat_math_model import COMBAT_MODIFIER_KEYS
from src.backend.features.character.schemas.session import (
    CharacterSessionBioDTO,
    CharacterSessionDocumentDTO,
    CharacterSessionItemsDTO,
)
from src.backend.features.items.resources.affixes.catalog import AFFIX_CATALOG
from src.backend.features.items.resources.affixes.schemas import (
    AffixCatalogEntryDTO,
    AffixDescriptiveDTO,
    AffixRollProfileDTO,
    AffixTechnicalDTO,
)
from src.backend.features.items.resources.modifier_contracts import MODIFIER_CONTRACTS, ModifierContractDTO


@pytest.mark.unit
def test_active_character_items_contract_defaults_to_empty_layout() -> None:
    document = CharacterSessionDocumentDTO.model_validate(
        {
            "char_id": 7,
            "user_id": "00000000-0000-0000-0000-000000000001",
            "bio": {
                "name": "Ada",
                "gender": "female",
                "created_at": "2026-05-05T00:00:00Z",
            },
            "updated_at": "2026-05-05T00:00:00Z",
        }
    )

    assert isinstance(document.bio, CharacterSessionBioDTO)
    assert isinstance(document.items, CharacterSessionItemsDTO)
    assert document.items.layout.equipment == {}
    assert document.items.layout.belt == {}
    assert document.items.by_id == {}


@pytest.mark.unit
def test_builder_wraps_active_character_attributes_and_equipped_item_mechanics() -> None:
    raw = CharacterCombatMathModelBuilder().build_raw(
        attributes={"strength": 15, "agility": 9},
        items={
            "layout": {
                "equipment": {
                    "main_hand": "weapon-1",
                    "chest_armor": "armor-1",
                },
                "belt": {"belt_slot_1": "potion-1"},
            },
            "by_id": {
                "weapon-1": {
                    "item_id": "weapon-1",
                    "item_type": "weapon",
                    "mechanics": {
                        "power": 7,
                        "damage_spread": 0.2,
                        "related_skill": "skill_macing",
                        "implicit_bonuses": {"accuracy_penalty": 0.1, "parry_chance": 0.1},
                    },
                    "tags": ["axe"],
                },
                "armor-1": {
                    "item_id": "armor-1",
                    "item_type": "armor",
                    "mechanics": {"power": 4, "bonuses": {"physical_resistance": 0.05}},
                },
                "potion-1": {
                    "item_id": "potion-1",
                    "item_type": "consumable",
                    "mechanics": {"power": 99},
                },
            },
        },
        skills={"skill_macing": 0.5, "skill_parrying": 0.25, "skill_shield_mastery": 0.5},
    )

    assert raw["attributes"]["strength"] == {"base": 15.0, "source": {}, "temp": {}}
    assert raw["attributes"]["agility"] == {"base": 9.0, "source": {}, "temp": {}}
    assert raw["rules"] == {"attribute_profile": "player"}
    assert raw["modifiers"]["main_hand_damage_base"]["base"] == 7.0
    assert raw["modifiers"]["main_hand_damage_spread"]["base"] == 0.2
    assert raw["modifiers"]["main_hand_accuracy"]["base"] == 0.0
    assert "item:weapon-1" not in raw["modifiers"]["main_hand_accuracy"]["source"]
    assert raw["modifiers"]["parry"]["base"] == 0.1
    assert raw["modifiers"]["parry"]["source"] == {}
    assert raw["modifiers"]["armor"]["base"] == 4.0
    assert raw["modifiers"]["physical_resistance"]["source"]["item:armor-1"] == 0.05
    assert set(raw["modifiers"]) == COMBAT_MODIFIER_KEYS
    assert raw["modifiers"]["item_damage_base"] == {"base": 0.0, "source": {}, "temp": {}}


@pytest.mark.unit
def test_builder_maps_shield_block_chance_without_skill_scaling() -> None:
    raw = CharacterCombatMathModelBuilder().build_raw(
        attributes={},
        items={
            "layout": {"equipment": {"off_hand": "shield-1"}},
            "by_id": {
                "shield-1": {
                    "item_id": "shield-1",
                    "item_type": "shield",
                    "mechanics": {"power": 6.6, "implicit_bonuses": {"shield_block_chance": 0.1}},
                    "tags": ["shield"],
                }
            },
        },
        skills={"skill_parrying": {"xp": 0.5}},
    )

    assert raw["modifiers"]["block"]["base"] == 0.1
    assert raw["modifiers"]["block"]["source"] == {}
    assert raw["modifiers"]["armor"]["base"] == 0.0
    assert raw["modifiers"]["shield_guard_power"]["base"] == 6.6


@pytest.mark.unit
def test_builder_does_not_count_feetwear_as_flat_armor() -> None:
    raw = CharacterCombatMathModelBuilder().build_raw(
        attributes={},
        items={
            "layout": {"equipment": {"feetwear": "travel-shoes-1"}},
            "by_id": {
                "travel-shoes-1": {
                    "item_id": "travel-shoes-1",
                    "item_type": "armor",
                    "slot": "feetwear",
                    "mechanics": {"power": 1.6},
                }
            },
        },
        skills={},
    )

    assert raw["modifiers"]["armor"]["base"] == 0.0


@pytest.mark.unit
def test_builder_routes_feetwear_concentration_regen_into_waterfall_modifiers() -> None:
    raw = CharacterCombatMathModelBuilder().build_raw(
        attributes={},
        items={
            "layout": {"equipment": {"feetwear": "boots-1"}},
            "by_id": {
                "boots-1": {
                    "item_id": "boots-1",
                    "item_type": "garment",
                    "slot": "feetwear",
                    "mechanics": {"implicit_bonuses": {"stamina_regen": 1.5}},
                }
            },
        },
        skills={},
    )

    assert raw["modifiers"]["stamina_regen"]["base"] == pytest.approx(2.5)


@pytest.mark.unit
def test_builder_counts_two_hand_weapon_as_main_hand_damage_source() -> None:
    raw = CharacterCombatMathModelBuilder().build_raw(
        attributes={},
        items={
            "layout": {"equipment": {"two_hand": "katana-1"}},
            "by_id": {
                "katana-1": {
                    "item_id": "katana-1",
                    "item_type": "weapon",
                    "slot": "two_hand",
                    "mechanics": {
                        "power": 9,
                        "damage_spread": 0.1,
                        "related_skill": "skill_swords",
                        "implicit_bonuses": {"accuracy_penalty": 0.12},
                    },
                }
            },
        },
        skills={"skill_swords": 1.25},
    )

    assert raw["modifiers"]["main_hand_damage_base"]["base"] == 9.0
    assert raw["modifiers"]["main_hand_damage_spread"]["base"] == 0.1
    assert raw["modifiers"]["main_hand_accuracy"]["base"] == 0.0
    assert "item:katana-1" not in raw["modifiers"]["main_hand_accuracy"]["source"]


@pytest.mark.unit
def test_builder_routes_weapon_armor_penetration_pct_to_equipped_hand() -> None:
    raw = CharacterCombatMathModelBuilder().build_raw(
        attributes={},
        items={
            "layout": {"equipment": {"main_hand": "stiletto-1", "off_hand": "stiletto-2"}},
            "by_id": {
                "stiletto-1": {
                    "item_id": "stiletto-1",
                    "item_type": "weapon",
                    "slot": "main_hand",
                    "mechanics": {
                        "power": 3,
                        "damage_spread": 0.07,
                        "implicit_bonuses": {"weapon_armor_penetration_pct": 0.10},
                    },
                },
                "stiletto-2": {
                    "item_id": "stiletto-2",
                    "item_type": "weapon",
                    "slot": "off_hand",
                    "mechanics": {
                        "power": 2,
                        "damage_spread": 0.07,
                        "implicit_bonuses": {"weapon_armor_penetration_pct": 0.08},
                    },
                },
            },
        },
        skills={},
    )

    assert raw["modifiers"]["main_hand_armor_penetration_pct"]["base"] == 0.10
    assert raw["modifiers"]["off_hand_armor_penetration_pct"]["base"] == 0.08


@pytest.mark.unit
def test_builder_adds_unarmed_main_hand_when_no_weapon_is_equipped() -> None:
    raw = CharacterCombatMathModelBuilder().build_raw(
        attributes={"strength": 15},
        items={"layout": {"equipment": {}}, "by_id": {}},
        skills={},
    )

    assert raw["modifiers"]["main_hand_damage_base"]["base"] == 15.0
    assert raw["modifiers"]["main_hand_damage_spread"]["base"] == 0.5
    assert raw["modifiers"]["main_hand_accuracy"]["base"] == 0.0


@pytest.mark.unit
def test_builder_applies_heavy_chest_dodge_cap_override() -> None:
    raw = CharacterCombatMathModelBuilder().build_raw(
        attributes={},
        items={
            "layout": {"equipment": {"chest_armor": "plate-1"}},
            "by_id": {
                "plate-1": {
                    "item_id": "plate-1",
                    "base_id": "plate_chest",
                    "item_type": "armor",
                    "mechanics": {"armor_class": "heavy", "power": 10},
                }
            },
        },
        skills={"skill_heavy_armor": 1.0},
    )

    assert raw["modifiers"]["dodge_cap"]["source"]["item:plate-1"] == "=0.35"


@pytest.mark.unit
def test_builder_applies_medium_chest_dodge_cap_penalty_and_skill_recovery() -> None:
    raw = CharacterCombatMathModelBuilder().build_raw(
        attributes={},
        items={
            "layout": {"equipment": {"chest_armor": "jerkin-1"}},
            "by_id": {
                "jerkin-1": {
                    "item_id": "jerkin-1",
                    "base_id": "jerkin",
                    "item_type": "armor",
                    "mechanics": {"armor_class": "medium", "power": 4},
                }
            },
        },
        skills={"skill_medium_armor": 0.5},
    )

    sources = raw["modifiers"]["dodge_cap"]["source"]

    assert sources["item:jerkin-1:medium_cap_penalty"] == pytest.approx(-0.10)
    assert sources["skill:skill_medium_armor"] == pytest.approx(0.05)


@pytest.mark.unit
def test_builder_applies_light_armor_dodge_cap_skill_boost() -> None:
    raw = CharacterCombatMathModelBuilder().build_raw(
        attributes={},
        items={
            "layout": {"equipment": {"chest_armor": "leather-1"}},
            "by_id": {
                "leather-1": {
                    "item_id": "leather-1",
                    "base_id": "leather_armor",
                    "item_type": "armor",
                    "mechanics": {"armor_class": "light", "power": 3},
                }
            },
        },
        skills={"skill_light_armor": 1.0},
    )

    assert raw["modifiers"]["dodge_cap"]["source"]["skill:skill_light_armor"] == pytest.approx(0.20)


@pytest.mark.unit
def test_builder_applies_rolled_affix_add_command_to_modifier_source() -> None:
    raw = CharacterCombatMathModelBuilder().build_raw(
        attributes={},
        items={
            "layout": {"equipment": {"ring": "ring-1"}},
            "by_id": {
                "ring-1": {
                    "item_id": "ring-1",
                    "item_type": "accessory",
                    "slot": "ring",
                    "mechanics": {
                        "affixes": [{"affix_id": "crit_chance", "value": 0.05, "source": "single:combat_offense"}]
                    },
                }
            },
        },
        skills={},
    )

    sources = raw["modifiers"]["crit_chance"]["source"]

    assert sources["item:ring-1:affix:crit_chance"] == "+0.05"
    value, formula = StatsWaterfallCalculator.evaluate_sources(sources, base_value=0.10)
    assert value == pytest.approx(0.15)
    assert formula == "(0.1 + 0.05)"


@pytest.mark.unit
def test_builder_applies_rolled_affix_add_command_to_attribute_source() -> None:
    raw = CharacterCombatMathModelBuilder().build_raw(
        attributes={"strength": 8},
        items={
            "layout": {"equipment": {"ring": "ring-1"}},
            "by_id": {
                "ring-1": {
                    "item_id": "ring-1",
                    "item_type": "accessory",
                    "slot": "ring",
                    "mechanics": {
                        "affixes": [{"affix_id": "attribute_strength", "value": 2, "source": "single:attributes"}]
                    },
                }
            },
        },
        skills={},
    )

    assert raw["attributes"]["strength"]["base"] == 8.0
    assert raw["attributes"]["strength"]["source"]["item:ring-1:affix:attribute_strength"] == "+2"


@pytest.mark.unit
def test_builder_keeps_world_only_affixes_out_of_combat_raw() -> None:
    raw = CharacterCombatMathModelBuilder().build_raw(
        attributes={},
        items={
            "layout": {"equipment": {"belt": "belt-1"}},
            "by_id": {
                "belt-1": {
                    "item_id": "belt-1",
                    "item_type": "belt",
                    "slot": "belt",
                    "mechanics": {
                        "affixes": [{"affix_id": "travel_speed", "value": 0.05, "source": "single:world_exploration"}]
                    },
                }
            },
        },
        skills={},
    )

    assert "travel_speed" not in raw["modifiers"]
    assert all("travel_speed" not in source for data in raw["modifiers"].values() for source in data["source"])


@pytest.mark.unit
def test_builder_accepts_affix_mult_command_from_modifier_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    contract = ModifierContractDTO(
        id="crit_chance_mult_test",
        target_field="crit_chance",
        operation="mult",
        value_kind="percent",
    )
    affix = AffixCatalogEntryDTO(
        id="crit_chance_mult_test",
        group="combat_offense",
        technical=AffixTechnicalDTO(
            modifier_id="crit_chance_mult_test",
            base_value=0.10,
            value_kind="multiplier_delta",
            roll_profile=AffixRollProfileDTO(step_spread=0.0, rounding="decimal", round_digits=4),
        ),
        descriptive=AffixDescriptiveDTO(
            display_name="Crit Mult Test",
            ui_template="+{value}% Crit",
            narrative_tags=("test",),
        ),
    )
    monkeypatch.setitem(MODIFIER_CONTRACTS, "crit_chance_mult_test", contract)
    monkeypatch.setitem(AFFIX_CATALOG, "crit_chance_mult_test", affix)

    raw = CharacterCombatMathModelBuilder().build_raw(
        attributes={},
        items={
            "layout": {"equipment": {"ring": "ring-1"}},
            "by_id": {
                "ring-1": {
                    "item_id": "ring-1",
                    "item_type": "accessory",
                    "slot": "ring",
                    "mechanics": {
                        "affixes": [{"affix_id": "crit_chance_mult_test", "value": 0.10, "source": "single:test"}]
                    },
                }
            },
        },
        skills={},
    )

    sources = raw["modifiers"]["crit_chance"]["source"]

    assert sources["item:ring-1:affix:crit_chance_mult_test"] == "*1.1"
    value, formula = StatsWaterfallCalculator.evaluate_sources(sources, base_value=0.20)
    assert value == pytest.approx(0.22)
    assert formula == "0.2 * 1.1"
