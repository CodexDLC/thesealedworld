from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.character.schemas.session import CharacterSessionDocumentDTO
from src.shared.enums.skill_enums import SkillProgressState

if TYPE_CHECKING:
    from src.backend.features.character.managers.session import CharacterSessionManager
    from src.backend.features.character.repositories import (
        CharacterAttributesRepository,
        CharacterRepository,
        SkillRepository,
    )


class CharacterSystemIntegrator:
    """Facade over character Redis session and persistent actor-state repositories."""

    def __init__(
        self,
        *,
        character_sessions: CharacterSessionManager,
        character_repo: CharacterRepository,
        attributes_repo: CharacterAttributesRepository,
        skill_repo: SkillRepository,
    ) -> None:
        self.character_sessions = character_sessions
        self.character_repo = character_repo
        self.attributes_repo = attributes_repo
        self.skill_repo = skill_repo

    async def sync_active_session(self, char_id: int) -> dict[str, Any]:
        document = await self.character_sessions.get_session(char_id)
        if document is None:
            raise ValueError(f"Active character session not found: char_id={char_id}")

        session_doc = CharacterSessionDocumentDTO.model_validate(document)
        synced_character = await self.character_repo.sync_active_session_snapshot(char_id, session_doc)
        if synced_character is None:
            raise ValueError(f"Character not found: char_id={char_id}")

        await self.attributes_repo.upsert_attributes(
            session_doc.char_id,
            {key: int(value) for key, value in session_doc.attributes.model_dump(mode="json").items()},
        )
        synced_skills = await self._sync_skills(session_doc)
        await self.character_sessions.clear_dirty(char_id)
        return {
            "char_id": char_id,
            "state": synced_character["state"],
            "location_id": synced_character["location_id"],
            "skills": synced_skills,
        }

    async def _sync_skills(self, session_doc: CharacterSessionDocumentDTO) -> list[str]:
        rows: list[dict[str, Any]] = []
        for skill_key, value in session_doc.skills.items():
            if isinstance(value, dict):
                total_xp = float(value.get("xp", value.get("total_xp", 0.0)) or 0.0)
                is_unlocked = bool(value.get("unlocked", True))
                progress_state = SkillProgressState(value.get("state") or SkillProgressState.PLUS.value)
            else:
                total_xp = float(value) if isinstance(value, (int, float, str)) else 0.0
                is_unlocked = True
                progress_state = SkillProgressState.PLUS
            rows.append(
                {
                    "character_id": session_doc.char_id,
                    "skill_key": skill_key,
                    "total_xp": total_xp,
                    "is_unlocked": is_unlocked,
                    "progress_state": progress_state,
                }
            )

        await self.skill_repo.upsert_progress_rows(rows)
        return [str(row["skill_key"]) for row in rows]
