import pytest

from src.backend.core.calculators.skill_progression_calculator import (
    SkillProgressionBatchInput,
    SkillProgressionCalculator,
    SkillProgressionEntry,
)
from src.backend.features.game_catalog.skills.dto import SkillDefinitionDTO


@pytest.mark.unit
def test_skill_progression_calculator_returns_rounded_reward_mapping() -> None:
    skill = SkillDefinitionDTO(
        skill_key="skill_swords",
        name_en="Swordsmanship",
        name_ru="Владение мечами",
        stat_weights={"strength": 2, "agility": 1, "endurance": 1},
        rate_mod=1.0,
        wall_mod=1.0,
    )

    rewards = SkillProgressionCalculator.calculate(
        SkillProgressionBatchInput(
            entries={
                "skill_swords": SkillProgressionEntry(
                    skill=skill,
                    attributes={"strength": 10, "agility": 5, "endurance": 5},
                    current_skill=0.0,
                    action_power=2.0,
                )
            }
        )
    )

    assert rewards == {"skill_swords": 0.0003}


@pytest.mark.unit
def test_skill_progression_calculator_accepts_free_xp_base_power() -> None:
    rewards = SkillProgressionCalculator.calculate(
        SkillProgressionBatchInput(
            entries={
                "free_xp": SkillProgressionEntry(
                    base_power=25.0,
                    action_power=2.0,
                    rate_mod=1.0,
                    wall_mod=0.0,
                )
            }
        )
    )

    assert rewards == {"free_xp": 0.0003}
