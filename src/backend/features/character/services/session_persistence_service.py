from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.backend.infrastructure.actor_state.models import Character, CharacterAttributes, SkillProgress
from src.backend.infrastructure.actor_state.schemas.session import CharacterSessionDocumentDTO
from src.shared.enums.skill_enums import SkillProgressState

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.backend.infrastructure.actor_state.managers.session import CharacterSessionManager


ATTRIBUTE_KEYS = (
    "strength",
    "agility",
    "endurance",
    "intellect",
    "memory",
    "mental",
    "perception",
    "projection",
    "prediction",
)


class CharacterSessionPersistenceService:
    def __init__(self, *, db_session: AsyncSession, character_sessions: CharacterSessionManager) -> None:
        self.db_session = db_session
        self.character_sessions = character_sessions

    async def sync_active_session_to_db(self, char_id: int) -> dict[str, Any]:
        document = await self.character_sessions.get_session(char_id)
        if document is None:
            raise ValueError(f"Active character session not found: char_id={char_id}")

        session_doc = CharacterSessionDocumentDTO.model_validate(document)
        character = await self.db_session.scalar(select(Character).where(Character.character_id == char_id))
        if character is None:
            raise ValueError(f"Character not found: char_id={char_id}")

        character.game_stage = str(session_doc.state)
        character.prev_game_stage = str(session_doc.prev_state) if session_doc.prev_state is not None else None
        character.location_id = session_doc.location.current
        character.prev_location_id = session_doc.location.prev
        character.vitals_snapshot = session_doc.vitals.model_dump(mode="json")
        character.active_sessions = {
            **session_doc.sessions.model_dump(mode="json"),
            "active_quest": session_doc.active_quest,
        }

        await self._sync_attributes(session_doc)
        synced_skills = await self._sync_skills(session_doc)
        await self.db_session.flush()
        return {
            "char_id": char_id,
            "state": character.game_stage,
            "location_id": character.location_id,
            "skills": synced_skills,
        }

    async def _sync_attributes(self, session_doc: CharacterSessionDocumentDTO) -> None:
        attributes = session_doc.attributes.model_dump(mode="json")
        row = {"character_id": session_doc.char_id, **{key: int(attributes[key]) for key in ATTRIBUTE_KEYS}}
        stmt = insert(CharacterAttributes).values(row)
        stmt = stmt.on_conflict_do_update(
            index_elements=[CharacterAttributes.character_id],
            set_={key: row[key] for key in ATTRIBUTE_KEYS},
        )
        await self.db_session.execute(stmt)

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

        if not rows:
            return []

        stmt = insert(SkillProgress).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=[SkillProgress.character_id, SkillProgress.skill_key],
            set_={
                "total_xp": stmt.excluded.total_xp,
                "is_unlocked": stmt.excluded.is_unlocked,
                "progress_state": stmt.excluded.progress_state,
            },
        )
        await self.db_session.execute(stmt)
        return [str(row["skill_key"]) for row in rows]
