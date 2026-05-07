import pytest

from src.backend.core.calculators.data.stats_formulas import MODIFIER_RULES as CORE_MODIFIER_RULES
from src.backend.core.calculators.stats_waterfall_calculator import StatsWaterfallCalculator
from src.backend.features.character.runtime import CharacterCombatMathModelBuilder
from src.backend.features.character.runtime.rules.attribute_modifiers import ATTRIBUTE_MODIFIER_RULES


@pytest.mark.unit
def test_core_calculator_uses_character_attribute_modifier_rules() -> None:
    assert CORE_MODIFIER_RULES is ATTRIBUTE_MODIFIER_RULES


@pytest.mark.unit
def test_character_raw_attributes_drive_combat_modifiers_through_waterfall() -> None:
    raw = CharacterCombatMathModelBuilder().build_raw(
        attributes={
            "strength": 15,
            "agility": 9,
            "endurance": 16,
            "mental": 13,
        },
        items={},
        skills={},
    )

    calculated, _ = StatsWaterfallCalculator.calculate_waterfall(raw)

    assert calculated["physical_damage"] == 15.0
    assert calculated["hp"] == 64.0
    assert calculated["en"] == 26.0
    assert calculated["stamina"] == 160.0
    assert calculated["evasion"] == 0.135
