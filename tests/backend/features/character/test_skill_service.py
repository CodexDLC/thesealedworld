from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.features.character.services import CharacterSkillService
from src.backend.features.game_catalog.skills.dto import SkillDefinitionDTO
from src.shared.enums.skill_enums import SkillProgressState


@pytest.mark.unit
async def test_character_skill_service_unlocks_valid_skills_in_db_and_redis() -> None:
    integrator = MagicMock()
    integrator.unlock_skills = AsyncMock()
    catalog = MagicMock()
    catalog.get.return_value = SkillDefinitionDTO(skill_key="skill_swords", name_en="Swordsmanship", name_ru="Мечи")
    service = CharacterSkillService(state_integrator=integrator, catalog=catalog)

    unlocked = await service.unlock_skills(7, ["skill_swords", "skill_swords"])

    assert unlocked == ["skill_swords"]
    integrator.unlock_skills.assert_awaited_once_with(
        7,
        ["skill_swords"],
        progress_state=SkillProgressState.PLUS,
    )


@pytest.mark.unit
async def test_character_skill_service_rejects_unknown_skill() -> None:
    catalog = MagicMock()
    catalog.get.return_value = None
    service = CharacterSkillService(state_integrator=MagicMock(), catalog=catalog)

    with pytest.raises(ValueError, match="Unknown skill keys"):
        await service.unlock_skills(7, ["unknown"])
