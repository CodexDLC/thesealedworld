import pytest

from src.backend.features.character.dto.modifiers import CombatModifiersDTO
from src.backend.features.character.runtime.combat_math_model import (
    COMBAT_MODIFIER_KEYS,
    CharacterCombatMathModelBuilder,
)
from src.backend.features.character.runtime.gear_score import CharacterGearScoreCalculator
from src.backend.features.character.runtime.rules.gear_score import GEAR_SCORE_WEIGHTS


@pytest.mark.unit
def test_gear_score_weights_cover_all_combat_modifiers() -> None:
    assert set(GEAR_SCORE_WEIGHTS) == set(CombatModifiersDTO.model_fields)


@pytest.mark.unit
def test_combat_math_model_outputs_only_combat_modifier_keys() -> None:
    raw = CharacterCombatMathModelBuilder().build_raw(
        attributes={"strength": 10},
        items={
            "layout": {"equipment": {"main_hand": "weapon-1"}},
            "by_id": {
                "weapon-1": {
                    "item_id": "weapon-1",
                    "item_type": "weapon",
                    "mechanics": {
                        "power": 7,
                        "implicit_bonuses": {
                            "physical_accuracy": 0.1,
                            "unknown_bonus": 99,
                        },
                    },
                }
            },
        },
        skills={},
    )

    assert set(raw["modifiers"]) <= COMBAT_MODIFIER_KEYS
    assert "unknown_bonus" not in raw["modifiers"]


@pytest.mark.unit
def test_gear_score_uses_waterfall_calculated_raw_and_equipment() -> None:
    base_ac = {
        "attributes": {
            "strength": 15,
            "agility": 9,
            "endurance": 16,
            "mental": 13,
        },
        "items": {},
        "skills": {},
    }
    equipped_ac = {
        **base_ac,
        "items": {
            "layout": {"equipment": {"main_hand": "weapon-1", "chest_armor": "armor-1"}},
            "by_id": {
                "weapon-1": {
                    "item_id": "weapon-1",
                    "item_type": "weapon",
                    "mechanics": {"power": 7, "implicit_bonuses": {"physical_accuracy": 0.1}},
                },
                "armor-1": {
                    "item_id": "armor-1",
                    "item_type": "armor",
                    "mechanics": {"power": 4, "bonuses": {"physical_resistance": 0.05}},
                },
            },
        },
    }

    calculator = CharacterGearScoreCalculator()

    assert calculator.calculate_from_active_character(equipped_ac) > calculator.calculate_from_active_character(base_ac)
