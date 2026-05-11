import pytest

from src.backend.core.calculators.skill_progression_calculator import (
    GLOBAL_BASE_RATE,
    GLOBAL_BASE_WALL,
    SkillProgressionBatchInput,
    SkillProgressionCalculator,
    SkillProgressionEntry,
)
from src.backend.features.game_catalog.skills.dto import SkillCategory, SkillDefinitionDTO, SkillGroup


@pytest.mark.unit
def test_skill_progression_calculator_uses_traction_against_resistance():
    skill = SkillDefinitionDTO(
        skill_key="skill_swords",
        name_en="Swordsmanship",
        name_ru="Владение мечами",
        category=SkillCategory.COMBAT,
        group=SkillGroup.COMBAT,
        stat_weights={"strength": 2, "agility": 1},
        rate_mod=1.0,
        wall_mod=1.0,
    )

    entry = SkillProgressionEntry(
        skill=skill,
        attributes={"strength": 10, "agility": 5},
        current_skill=0.5,
    )
    base_power = SkillProgressionCalculator.calculate_base_power(entry)
    delta = SkillProgressionCalculator.calculate_delta(entry)

    assert base_power == 25
    assert GLOBAL_BASE_RATE * skill.rate_mod == 0.00005
    assert GLOBAL_BASE_WALL * skill.wall_mod == 100.0
    assert 1.0 + (entry.current_skill * GLOBAL_BASE_WALL * skill.wall_mod) == 51.0
    assert delta == pytest.approx((25 * 0.00005) / 51.0)


@pytest.mark.unit
def test_skill_progression_calculator_returns_award_mapping_without_persistence_clamp():
    skill = SkillDefinitionDTO(
        skill_key="skill_test",
        name_en="Test",
        name_ru="Тест",
        stat_weights={"strength": 2},
        rate_mod=2.0,
        wall_mod=0.1,
    )

    rewards = SkillProgressionCalculator.calculate(
        SkillProgressionBatchInput(
            entries={
                "skill_test": SkillProgressionEntry(
                    skill=skill,
                    attributes={"strength": 10},
                    current_skill=0.5,
                    action_power=2.0,
                )
            }
        )
    )

    assert rewards == {"skill_test": 0.0007}
