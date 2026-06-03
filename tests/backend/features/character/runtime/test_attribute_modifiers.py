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


def _effective(stat: float) -> float:
    return stat * stat / 11.0


def _approx_effective(value: float) -> pytest.approx:
    return pytest.approx(round(value, 4))


@pytest.mark.unit
def test_core_calculator_uses_character_attribute_modifier_rules() -> None:
    assert CORE_MODIFIER_RULES is ATTRIBUTE_MODIFIER_RULES
    assert ATTRIBUTE_RULE_PROFILES["player"]["hp"] == ATTRIBUTE_RULE_PROFILES["player:naked"]["hp"]
    assert ATTRIBUTE_RULE_PROFILES["player:light"]["hp"] == ATTRIBUTE_RULE_PROFILES["player:naked"]["hp"]
    assert ATTRIBUTE_RULE_PROFILES["player:medium"]["hp"] == ATTRIBUTE_RULE_PROFILES["player:naked"]["hp"]
    assert ATTRIBUTE_RULE_PROFILES["player:heavy"]["hp"] == ATTRIBUTE_RULE_PROFILES["player:naked"]["hp"]
    assert ATTRIBUTE_RULE_PROFILES["player"]["hp"] == {"endurance": 3.0}
    assert ATTRIBUTE_RULE_PROFILES["monster:humanoid"]["hp"] == {"endurance": 3.0}
    assert ATTRIBUTE_RULE_PROFILES["monster:beast"]["hp"] == {"endurance": 3.0}
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
    effective_strength = _effective(15)
    effective_agility = _effective(9)
    effective_endurance = _effective(16)
    effective_intellect = _effective(11)
    effective_memory = _effective(10)
    effective_mental = _effective(13)
    effective_perception = _effective(8)
    effective_projection = _effective(7)
    effective_prediction = _effective(6)

    assert calculated["physical_strength_power"] == _approx_effective(effective_strength)
    assert calculated["physical_agility_power"] == _approx_effective(effective_agility)
    assert calculated["physical_endurance_power"] == _approx_effective(effective_endurance)
    assert calculated["physical_suppression"] == _approx_effective(effective_strength * 0.02)
    assert calculated["magical_damage"] == _approx_effective(effective_intellect)
    assert calculated["magical_penetration"] == _approx_effective(effective_intellect * 0.02)
    assert calculated["hp"] == _approx_effective(effective_endurance * 3.0)
    assert calculated["en"] == _approx_effective(effective_mental * 2.0)
    assert calculated["stamina"] == _approx_effective(effective_projection * 2.7)
    assert calculated["hp_regen"] == _approx_effective(effective_endurance * 0.1)
    assert calculated["en_regen"] == _approx_effective(effective_mental * 0.25)
    assert calculated["stamina_regen"] == _approx_effective(1.0 + (effective_projection * 0.2))
    assert calculated["physical_resistance"] == _approx_effective(effective_endurance * 0.02)
    assert calculated["magic_resist"] == _approx_effective(effective_mental * 0.02)
    assert calculated["poison_resistance"] == _approx_effective(effective_endurance * 0.02)
    assert calculated["bleed_resistance"] == _approx_effective(effective_endurance * 0.02)
    assert calculated["environment_bio_resistance"] == _approx_effective(effective_endurance * 0.02)
    assert calculated["control_resistance"] == _approx_effective(effective_mental * 0.02)
    assert calculated["mental_resistance"] == _approx_effective(effective_mental * 0.02)
    assert calculated["fire_resistance"] == _approx_effective(effective_mental * 0.02)
    assert calculated["arcane_resistance"] == _approx_effective(effective_mental * 0.02)
    assert calculated["evasion"] == _approx_effective(effective_agility * 0.02)
    assert calculated["anti_dodge_chance"] == _approx_effective(effective_perception * 0.03)
    assert calculated["counter_attack_chance"] == _approx_effective(
        (effective_memory * 0.0025) + (effective_prediction * 0.0015)
    )
    assert calculated["initiative"] == _approx_effective(effective_agility * 0.5)
    assert calculated["armor"] == 0.0
    assert calculated["block"] == 0.0
    assert calculated["parry"] == 0.0


@pytest.mark.unit
def test_humanoid_monster_attribute_profile_uses_endurance_hp_without_hp_regen() -> None:
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

    assert calculated["hp"] == _approx_effective(_effective(16) * 3.0)
    assert calculated.get("hp_regen", 0.0) == 0.0


@pytest.mark.unit
def test_beast_monster_attribute_profile_uses_endurance_hp_without_hp_regen() -> None:
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

    assert calculated["hp"] == _approx_effective(_effective(16) * 3.0)
    assert calculated.get("hp_regen", 0.0) == 0.0


@pytest.mark.unit
def test_effective_curve_keeps_medium_endurance_minions_from_inflated_hp() -> None:
    raw = {
        "attributes": {
            "endurance": {"base": 11, "source": {}, "temp": {}},
        },
        "modifiers": {},
        "rules": {"attribute_profile": "monster:beast"},
    }

    calculated, _ = StatsWaterfallCalculator.calculate_waterfall(raw)

    assert calculated["hp"] == _approx_effective(33.0)
