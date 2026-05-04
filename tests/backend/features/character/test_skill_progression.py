import pytest

from src.backend.features.character.runtime import SkillProgressionInput, calculate_skill_delta
from src.backend.features.game_catalog.skills.dto import SkillCategory, SkillDefinitionDTO, SkillGroup


@pytest.mark.unit
def test_calculate_skill_delta_uses_traction_against_resistance():
    skill = SkillDefinitionDTO(
        skill_key="skill_swords",
        name_en="Swordsmanship",
        name_ru="Владение мечами",
        category=SkillCategory.COMBAT,
        group=SkillGroup.WEAPON_MASTERY,
        stat_weights={"strength": 2, "agility": 1},
        rate_mod=1.0,
        wall_mod=1.0,
    )

    result = calculate_skill_delta(
        SkillProgressionInput(
            skill=skill,
            attributes={"strength": 10, "agility": 5},
            current_skill=0.5,
        )
    )

    assert result.base_power == 25
    assert result.effective_rate == 0.000005
    assert result.effective_wall == 100.0
    assert result.resistance == 51.0
    assert result.delta == pytest.approx((25 * 0.000005) / 51.0)
    assert result.next_skill == pytest.approx(0.5 + result.delta)


@pytest.mark.unit
def test_calculate_skill_delta_clamps_next_skill_to_cap():
    skill = SkillDefinitionDTO(
        skill_key="skill_test",
        name_en="Test",
        name_ru="Тест",
        stat_weights={"strength": 10_000_000},
        rate_mod=100.0,
        wall_mod=0.1,
    )

    result = calculate_skill_delta(
        SkillProgressionInput(skill=skill, attributes={"strength": 10_000_000}, current_skill=0.99)
    )

    assert result.next_skill == 1.0
