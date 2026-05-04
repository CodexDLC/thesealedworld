from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.game_catalog.skills.services import SkillCatalogService
from src.shared.enums.skill_enums import SkillProgressState

if TYPE_CHECKING:
    from src.backend.infrastructure.actor_state.managers.session import CharacterSessionManager
    from src.backend.infrastructure.actor_state.repositories import SkillRepository


class CharacterSkillService:
    def __init__(
        self,
        *,
        skill_repo: SkillRepository,
        character_sessions: CharacterSessionManager,
        catalog: SkillCatalogService | None = None,
    ) -> None:
        self.skill_repo = skill_repo
        self.character_sessions = character_sessions
        self.catalog = catalog or SkillCatalogService()

    async def unlock_skills(
        self,
        char_id: int,
        skill_keys: list[str],
        *,
        progress_state: SkillProgressState = SkillProgressState.PLUS,
    ) -> list[str]:
        valid_skill_keys = self._validate_skill_keys(skill_keys)
        if not valid_skill_keys:
            return []

        await self.skill_repo.unlock_skills(char_id, valid_skill_keys, progress_state=progress_state)
        await self.character_sessions.unlock_skills(char_id, valid_skill_keys)
        return valid_skill_keys

    def _validate_skill_keys(self, skill_keys: list[str]) -> list[str]:
        unique_skill_keys = list(dict.fromkeys(skill_key for skill_key in skill_keys if skill_key))
        unknown = [skill_key for skill_key in unique_skill_keys if self.catalog.get(skill_key) is None]
        if unknown:
            raise ValueError(f"Unknown skill keys: {', '.join(unknown)}")
        return unique_skill_keys
