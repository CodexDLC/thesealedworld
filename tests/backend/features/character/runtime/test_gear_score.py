import pytest

from src.backend.features.character.dto.modifiers import CombatModifiersDTO
from src.backend.features.character.runtime.combat_math_model import (
    COMBAT_MODIFIER_KEYS,
    CharacterCombatMathModelBuilder,
)
from src.backend.features.character.runtime.gear_score import CharacterGearScoreCalculator
from src.backend.features.character.runtime.rules.gear_score import GEAR_SCORE_WEIGHTS
from src.backend.features.character.services import StartingImprintService
from src.backend.features.items.dto.instance import ItemGenerationRequestDTO
from src.backend.features.items.runtime.item_factory import ItemFactory


@pytest.mark.unit
def test_gear_score_weights_are_combat_runtime_subset() -> None:
    assert set(GEAR_SCORE_WEIGHTS) <= set(CombatModifiersDTO.model_fields)
    assert "environment_cold_resistance" not in GEAR_SCORE_WEIGHTS
    assert "environment_heat_resistance" not in GEAR_SCORE_WEIGHTS
    assert "environment_gravity_resistance" not in GEAR_SCORE_WEIGHTS
    assert "environment_bio_resistance" not in GEAR_SCORE_WEIGHTS
    assert "resource_cost_reduction" not in GEAR_SCORE_WEIGHTS
    assert "initiative" not in GEAR_SCORE_WEIGHTS
    assert "crit_power" not in GEAR_SCORE_WEIGHTS
    assert "control_resistance" not in GEAR_SCORE_WEIGHTS
    assert "physical_damage" not in GEAR_SCORE_WEIGHTS
    assert "physical_strength_power" not in GEAR_SCORE_WEIGHTS
    assert "physical_agility_power" not in GEAR_SCORE_WEIGHTS
    assert "physical_endurance_power" not in GEAR_SCORE_WEIGHTS


@pytest.mark.unit
def test_gear_score_does_not_add_constant_base_or_default_modifier_offset() -> None:
    score = CharacterGearScoreCalculator().calculate_from_active_character(
        {
            "attributes": {},
            "items": {},
            "skills": {},
        }
    )

    assert score == 1


@pytest.mark.unit
def test_gear_score_accepts_fractional_waterfall_vitals() -> None:
    score = CharacterGearScoreCalculator.calculate_from_calculated(
        {
            "hp": 53.3333,
            "en": 8.6667,
            "main_hand_damage_base": 15.0,
        }
    )

    assert score >= 1


@pytest.mark.unit
def test_gear_score_ignores_environment_only_modifiers() -> None:
    score = CharacterGearScoreCalculator.calculate_from_calculated(
        {
            "environment_cold_resistance": 10.0,
            "environment_heat_resistance": 10.0,
            "environment_gravity_resistance": 10.0,
            "environment_bio_resistance": 10.0,
        }
    )

    assert score == 1


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
                            "main_hand_accuracy_penalty": 0.1,
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
                    "mechanics": {"power": 7, "implicit_bonuses": {"main_hand_accuracy_penalty": 0.1}},
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


@pytest.mark.unit
def test_gear_score_uses_assembled_weapon_power_after_mastery() -> None:
    base_ac = {
        "attributes": {
            "strength": 17,
            "agility": 10,
            "endurance": 8,
        },
        "items": {
            "layout": {"equipment": {"main_hand": "weapon-1"}},
            "by_id": {
                "weapon-1": {
                    "item_id": "weapon-1",
                    "item_type": "weapon",
                    "slot": "main_hand",
                    "mechanics": {
                        "power": 7,
                        "damage_spread": 0.12,
                        "skill_key": "skill_fencing",
                    },
                },
            },
        },
    }
    novice_ac = {**base_ac, "skills": {"skill_fencing": 0.0}}
    master_ac = {**base_ac, "skills": {"skill_fencing": 1.0}}

    calculator = CharacterGearScoreCalculator()

    assert calculator.calculate_from_active_character(master_ac) > calculator.calculate_from_active_character(novice_ac)


@pytest.mark.unit
def test_gear_score_breakdown_from_active_character_matches_total_and_skills() -> None:
    active_character = {
        "attributes": {"strength": 12},
        "items": {},
        "skills": {
            "skill_swords": {"xp": 0.4},
            "skill_light_armor": {"xp": 0.8},
            "skill_scouting": {"xp": 1.0},
        },
    }

    breakdown = CharacterGearScoreCalculator().calculate_breakdown_from_active_character(active_character)

    assert breakdown["skills"] == 220.0
    assert breakdown["total"] == CharacterGearScoreCalculator().calculate_from_active_character(active_character)


@pytest.mark.unit
def test_gear_score_adds_each_normalized_skill_as_points() -> None:
    novice_score = CharacterGearScoreCalculator.calculate_from_raw(
        {},
        skills={"skill_fencing": 0.25, "skill_light_armor": {"xp": 0.25}, "skill_pathfinder": 1.0},
    )
    master_score = CharacterGearScoreCalculator.calculate_from_raw(
        {},
        skills={"skill_fencing": 1.0, "skill_light_armor": {"xp": 1.0}, "skill_pathfinder": 1.0},
    )
    master_breakdown = CharacterGearScoreCalculator.calculate_breakdown_from_raw(
        {},
        skills={"skill_fencing": 1.0, "skill_light_armor": {"xp": 1.0}, "skill_pathfinder": 1.0},
    )

    assert master_breakdown["skills"] == 300.0
    assert master_score - novice_score == 150


@pytest.mark.unit
def test_gear_score_breakdown_exposes_skill_score_component() -> None:
    breakdown = CharacterGearScoreCalculator.calculate_breakdown_from_raw(
        {"modifiers": {"armor": {"base": 10.0}}},
        skills={"skill_heavy_armor": 1.0, "skill_shield_mastery": 0.5, "skill_adaptation": 1.0},
    )

    assert breakdown["skills"] == 250.0
    assert breakdown["total"] >= 250


@pytest.mark.unit
def test_gear_score_breakdown_splits_combat_value_by_role() -> None:
    breakdown = CharacterGearScoreCalculator.calculate_breakdown_from_calculated(
        {
            "hp": 100.0,
            "main_hand_damage_base": 20.0,
            "main_hand_accuracy_penalty": 0.10,
            "armor": 10.0,
            "block": 0.20,
            "hand_size": 4.0,
        }
    )

    assert breakdown["total"] >= 1
    assert breakdown["offense"] > 0
    assert breakdown["defense"] > 0
    assert breakdown["resources"] > 0
    assert breakdown["utility"] > 0
    assert round(breakdown["offense"] + breakdown["defense"] + breakdown["resources"] + breakdown["utility"]) >= breakdown[
        "total"
    ]


@pytest.mark.unit
def test_gear_score_ignores_garment_power_without_combat_modifiers() -> None:
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
            "layout": {"equipment": {"feetwear": "boots-1"}},
            "by_id": {
                "boots-1": {
                    "item_id": "boots-1",
                    "item_type": "garment",
                    "slot": "feetwear",
                    "mechanics": {"power": 8},
                },
            },
        },
    }

    calculator = CharacterGearScoreCalculator()

    assert calculator.calculate_from_active_character(equipped_ac) == calculator.calculate_from_active_character(base_ac)


@pytest.mark.unit
def test_gear_score_counts_jewelry_power_as_defensive_magic_armor() -> None:
    breakdown = CharacterGearScoreCalculator.calculate_breakdown_from_calculated({"magic_armor": 5.0})

    assert breakdown["total"] >= 1
    assert breakdown["defense"] == pytest.approx(4.0)
    assert breakdown["offense"] == 0.0


@pytest.mark.unit
def test_starter_breaker_imprint_is_not_inflated_by_survival_garments() -> None:
    active_character = _build_starting_imprint_active_character("starter_breaker_01")

    score = CharacterGearScoreCalculator().calculate_from_active_character(active_character)

    assert 220 <= score <= 320


def _build_starting_imprint_active_character(imprint_key: str) -> dict[str, object]:
    build = StartingImprintService().build(imprint_key)
    item_factory = ItemFactory()
    equipment: dict[str, str] = {}
    by_id: dict[str, dict[str, object]] = {}
    for index, base_id in enumerate(build.item_base_ids, start=1):
        item = item_factory.generate(
            ItemGenerationRequestDTO(
                base_id=base_id,
                rarity_tier=0,
                source="test:starting_imprint",
                request_ai_text=False,
            )
        )
        item_id = f"item-{index}"
        equipment[item.slot] = item_id
        by_id[item_id] = {
            "item_id": item_id,
            "base_id": item.base_id,
            "item_type": item.item_type,
            "slot": item.slot,
            "mechanics": item.mechanics,
            "tags": list(item.narrative_tags),
        }
    return {
        "attributes": build.attributes,
        "skills": {
            skill_key: {"xp": xp, "unlocked": True, "state": "PLUS"} for skill_key, xp in build.skill_xp.items()
        },
        "items": {"layout": {"equipment": equipment}, "by_id": by_id},
    }
