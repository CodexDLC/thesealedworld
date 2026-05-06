import pytest

from src.backend.features.character.runtime import CharacterCombatMathModelBuilder
from src.backend.features.character.runtime.combat_math_model import COMBAT_MODIFIER_KEYS
from src.backend.features.character.schemas.session import (
    CharacterSessionBioDTO,
    CharacterSessionDocumentDTO,
    CharacterSessionItemsDTO,
)


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
                    "belt_slot_1": None,
                },
                "belt": {"slot_1": "potion-1"},
            },
            "by_id": {
                "weapon-1": {
                    "item_id": "weapon-1",
                    "item_type": "weapon",
                    "mechanics": {
                        "power": 7,
                        "damage_spread": 0.2,
                        "implicit_bonuses": {"physical_accuracy": 0.1, "parry_chance": 0.1},
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
        skills={"skill_parrying": 25, "skill_shield_mastery": 50},
    )

    assert raw["attributes"]["strength"] == {"base": 15.0, "source": {}, "temp": {}}
    assert raw["attributes"]["agility"] == {"base": 9.0, "source": {}, "temp": {}}
    assert raw["modifiers"]["main_hand_damage_base"]["source"]["item:weapon-1"] == 7.0
    assert raw["modifiers"]["main_hand_damage_spread"]["source"]["item:weapon-1"] == 0.2
    assert raw["modifiers"]["accuracy"]["source"]["item:weapon-1"] == 0.1
    assert raw["modifiers"]["parry"]["source"]["item:weapon-1"] == 0.1
    assert raw["modifiers"]["parry"]["source"]["skill:skill_parrying:item:weapon-1"] == 0.1
    assert raw["modifiers"]["armor"]["source"]["item:armor-1"] == 4.0
    assert raw["modifiers"]["physical_resistance"]["source"]["item:armor-1"] == 0.05
    assert set(raw["modifiers"]) == COMBAT_MODIFIER_KEYS
    assert raw["modifiers"]["item_damage_base"] == {"base": 0.0, "source": {}, "temp": {}}


@pytest.mark.unit
def test_builder_applies_shield_mastery_as_precombat_source() -> None:
    raw = CharacterCombatMathModelBuilder().build_raw(
        attributes={},
        items={
            "layout": {"equipment": {"off_hand": "shield-1"}},
            "by_id": {
                "shield-1": {
                    "item_id": "shield-1",
                    "item_type": "shield",
                    "mechanics": {"implicit_bonuses": {"shield_block_chance": 0.2}},
                    "tags": ["shield"],
                }
            },
        },
        skills={"skill_shield_mastery": {"xp": 50}},
    )

    assert raw["modifiers"]["block"]["source"]["item:shield-1"] == 0.2
    assert raw["modifiers"]["block"]["source"]["skill:skill_shield_mastery:item:shield-1"] == pytest.approx(0.15)


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
                    "mechanics": {"power": 9, "damage_spread": 0.1},
                }
            },
        },
        skills={},
    )

    assert raw["modifiers"]["main_hand_damage_base"]["source"]["item:katana-1"] == 9.0
    assert raw["modifiers"]["main_hand_damage_spread"]["source"]["item:katana-1"] == 0.1
