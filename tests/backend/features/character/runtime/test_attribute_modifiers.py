import pytest

from src.backend.core.calculators.data.stats_formulas import (
    ATTRIBUTE_RULE_PROFILES,
)
from src.backend.core.calculators.data.stats_formulas import (
    MODIFIER_RULES as CORE_MODIFIER_RULES,
)
from src.backend.core.calculators.stats_waterfall_calculator import StatsWaterfallCalculator
from src.backend.features.character.runtime import CharacterCombatMathModelBuilder
from src.backend.features.character.runtime.rules.attribute_modifiers import ATTRIBUTE_MODIFIER_RULES


@pytest.mark.unit
def test_core_calculator_uses_character_attribute_modifier_rules() -> None:
    assert CORE_MODIFIER_RULES is ATTRIBUTE_MODIFIER_RULES
    assert ATTRIBUTE_RULE_PROFILES["player"] is ATTRIBUTE_MODIFIER_RULES
    assert "hp_regen" not in ATTRIBUTE_RULE_PROFILES["monster:humanoid"]
    assert "hp_regen" not in ATTRIBUTE_RULE_PROFILES["monster:beast"]


@pytest.mark.unit
def test_character_raw_attributes_drive_combat_modifiers_through_waterfall() -> None:
    raw = CharacterCombatMathModelBuilder().build_raw(
        attributes={
            "strength": 15,
            "agility": 9,
            "endurance": 16,
            "intellect": 11,
            "memory": 10,
            "mental": 13,
            "perception": 8,
            "projection": 7,
            "prediction": 6,
        },
        items={},
        skills={},
    )

    calculated, _ = StatsWaterfallCalculator.calculate_waterfall(raw)

    assert calculated["physical_damage"] == 0.0
    assert calculated["physical_strength_power"] == 15.0
    assert calculated["physical_agility_power"] == 9.0
    assert calculated["physical_endurance_power"] == 16.0
    assert calculated["physical_suppression"] == 0.3
    assert calculated["magical_damage"] == 11.0
    assert calculated["magical_penetration"] == 0.22
    assert calculated["hp"] == pytest.approx(53.3333)
    assert calculated["en"] == pytest.approx(34.0)
    assert calculated["stamina"] == pytest.approx(35.0)
    assert calculated["hp_regen"] == pytest.approx(1.3333)
    assert calculated["en_regen"] == pytest.approx(5.6667)
    assert calculated["stamina_regen"] == pytest.approx(3.1)
    assert calculated["physical_resistance"] == 0.32
    assert calculated["magic_resist"] == 0.26
    assert calculated["poison_resistance"] == 0.32
    assert calculated["bleed_resistance"] == 0.32
    assert calculated["environment_bio_resistance"] == 0.32
    assert calculated["control_resistance"] == 0.26
    assert calculated["mental_resistance"] == 0.26
    assert calculated["fire_resistance"] == 0.26
    assert calculated["arcane_resistance"] == 0.26
    assert calculated["evasion"] == 0.45
    assert calculated["anti_dodge_chance"] == 0.24
    assert calculated["counter_attack_chance"] == 0.034
    assert calculated["initiative"] == 4.5
    assert calculated["armor"] == 0.0
    assert calculated["block"] == 0.0
    assert calculated["parry"] == 0.0


@pytest.mark.unit
def test_humanoid_monster_attribute_profile_uses_body_average_for_hp_without_hp_regen() -> None:
    raw = {
        "attributes": {
            "strength": {"base": 15, "source": {}, "temp": {}},
            "agility": {"base": 8, "source": {}, "temp": {}},
            "endurance": {"base": 16, "source": {}, "temp": {}},
        },
        "modifiers": {},
        "rules": {"attribute_profile": "monster:humanoid"},
    }

    calculated, _ = StatsWaterfallCalculator.calculate_waterfall(raw)

    assert calculated["hp"] == pytest.approx(39.0)
    assert calculated.get("hp_regen", 0.0) == 0.0


@pytest.mark.unit
def test_beast_monster_attribute_profile_uses_body_average_for_hp_without_hp_regen() -> None:
    raw = {
        "attributes": {
            "strength": {"base": 15, "source": {}, "temp": {}},
            "agility": {"base": 8, "source": {}, "temp": {}},
            "endurance": {"base": 16, "source": {}, "temp": {}},
        },
        "modifiers": {},
        "rules": {"attribute_profile": "monster:beast"},
    }

    calculated, _ = StatsWaterfallCalculator.calculate_waterfall(raw)

    assert calculated["hp"] == pytest.approx(65.0)
    assert calculated.get("hp_regen", 0.0) == 0.0
