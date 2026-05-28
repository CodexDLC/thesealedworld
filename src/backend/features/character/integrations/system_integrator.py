from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.character.schemas.session import CharacterSessionDocumentDTO
from src.shared.enums.skill_enums import SkillProgressState

if TYPE_CHECKING:
    from src.backend.features.character.repositories import (
        CharacterAttributesRepository,
        CharacterProgressionRepository,
        CharacterRepository,
        SkillRepository,
        SymbioteRepository,
    )
    from src.backend.features.expedition import CharacterExpeditionRepository
    from src.backend.infrastructure.actor_state.managers import CharacterSessionManager


class CharacterSystemIntegrator:
    """Facade over character Redis session and persistent actor-state repositories."""

    def __init__(
        self,
        *,
        character_sessions: CharacterSessionManager,
        character_repo: CharacterRepository,
        attributes_repo: CharacterAttributesRepository,
        skill_repo: SkillRepository,
        progression_repo: CharacterProgressionRepository | None = None,
        symbiote_repo: SymbioteRepository | None = None,
        expedition_repo: CharacterExpeditionRepository | None = None,
    ) -> None:
        self.character_sessions = character_sessions
        self.character_repo = character_repo
        self.attributes_repo = attributes_repo
        self.skill_repo = skill_repo
        self.progression_repo = progression_repo
        self.symbiote_repo = symbiote_repo
        self.expedition_repo = expedition_repo

    async def sync_active_session(self, char_id: int) -> dict[str, Any]:
        document = await self.character_sessions.get_session(char_id)
        if document is None:
            raise ValueError(f"Active character session not found: char_id={char_id}")

        session_doc = CharacterSessionDocumentDTO.model_validate(document)
        dirty_marker = document.get("sync_dirty")
        dirty_targets = self._dirty_targets(dirty_marker)
        active_expedition = (
            await self.expedition_repo.get_active_for_character(char_id) if self.expedition_repo else None
        )
        unsafe_runtime = active_expedition is not None

        synced_character: dict[str, Any] | None = None
        if not unsafe_runtime and (dirty_targets is None or dirty_targets.get("character") is True):
            synced_character = await self.character_repo.sync_active_session_snapshot(char_id, session_doc)
            if synced_character is None:
                raise ValueError(f"Character not found: char_id={char_id}")

        if not unsafe_runtime and (dirty_targets is None or dirty_targets.get("attributes") is True):
            await self.attributes_repo.upsert_attributes(
                session_doc.char_id,
                {key: int(value) for key, value in session_doc.attributes.model_dump(mode="json").items()},
            )

        synced_skills: list[str] = []
        if not unsafe_runtime and (dirty_targets is None or dirty_targets.get("skills") is True):
            synced_skills = await self._sync_skills(session_doc)
            if self.progression_repo is not None:
                await self.progression_repo.set_free_xp(
                    session_doc.char_id,
                    float(session_doc.progression.free_xp or 0.0),
                )
        if (
            not unsafe_runtime
            and self.symbiote_repo is not None
            and (dirty_targets is None or dirty_targets.get("symbiote") is True)
        ):
            await self.symbiote_repo.upsert_from_session(
                session_doc.char_id,
                session_doc.symbiote.model_dump(mode="json"),
            )
        await self.character_sessions.clear_dirty(char_id, generation=self._dirty_generation(dirty_marker))
        return {
            "char_id": char_id,
            "state": synced_character["state"] if synced_character else str(session_doc.state),
            "location_id": synced_character["location_id"] if synced_character else session_doc.location.current,
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

    @staticmethod
    def _dirty_targets(marker: Any) -> dict[str, bool] | None:
        """Return explicit dirty targets, or None for legacy/full-sync markers."""
        if not isinstance(marker, dict) or marker.get("dirty") is not True:
            return None

        raw_targets = marker.get("targets")
        if not isinstance(raw_targets, dict):
            return None

        return {str(key): value is True for key, value in raw_targets.items()}

    @staticmethod
    def _dirty_generation(marker: Any) -> float | None:
        if not isinstance(marker, dict):
            return None
        value = marker.get("generation")
        return float(value) if isinstance(value, (int, float)) else None
