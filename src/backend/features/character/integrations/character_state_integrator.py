from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from src.backend.config.settings import settings
from src.backend.core.exceptions import BusinessLogicException
from src.backend.features.character.runtime import CharacterVitalsCalculator
from src.backend.features.character.schemas.session import (
    CharacterSessionAttributesDTO,
    CharacterSessionBioDTO,
    CharacterSessionDocumentDTO,
    CharacterSessionLocationDTO,
    CharacterSessionSymbioteDTO,
)
from src.shared.enums.skill_enums import SkillProgressState

if TYPE_CHECKING:
    from uuid import UUID

    from src.backend.features.character.managers.session import CharacterSessionManager
    from src.backend.features.character.models.character import Character
    from src.backend.features.character.repositories import CharacterRepository, SkillRepository
    from src.backend.features.character.schemas.session import CharacterGender


@dataclass(frozen=True)
class ActiveCharacterDocument:
    key: str
    document: dict[str, Any]


class CharacterStateIntegrator:
    """Facade over active character runtime state and persistent actor-state rows."""

    def __init__(
        self,
        *,
        character_sessions: CharacterSessionManager,
        character_repo: CharacterRepository,
        skill_repo: SkillRepository,
    ) -> None:
        self.character_sessions = character_sessions
        self.character_repo = character_repo
        self.skill_repo = skill_repo

    async def get_actor_core(self, user_id: UUID, char_id: int) -> ActiveCharacterDocument:
        session_doc = await self._get_or_initialize_session_doc(user_id, char_id)
        return ActiveCharacterDocument(
            key=self.character_sessions.build_key(char_id),
            document=session_doc.model_dump(mode="json"),
        )

    async def get_status_document(self, user_id: UUID, char_id: int) -> dict[str, Any]:
        session_doc = await self._get_or_initialize_session_doc(user_id, char_id)
        previous_last_update = session_doc.vitals.last_update
        updated_vitals = CharacterVitalsCalculator.apply_regen(session_doc.vitals)
        if updated_vitals.last_update != previous_last_update:
            session_doc.vitals = updated_vitals
            session_doc.updated_at = datetime.now(UTC)
            await self.character_sessions.update_session(char_id, session_doc.model_dump(mode="json"))
        return session_doc.model_dump(mode="json")

    async def unlock_skills(
        self,
        char_id: int,
        skill_keys: list[str],
        *,
        progress_state: SkillProgressState = SkillProgressState.PLUS,
    ) -> None:
        await self.skill_repo.unlock_skills(char_id, skill_keys, progress_state=progress_state)
        await self.character_sessions.unlock_skills(char_id, skill_keys)

    async def _get_or_initialize_session_doc(self, user_id: UUID, char_id: int) -> CharacterSessionDocumentDTO:
        character = await self.character_repo.get_by_id_and_user_id(char_id, user_id)
        if character is None:
            raise BusinessLogicException("Character is unavailable")

        document = await self.character_sessions.get_session(char_id)
        if document is None:
            return await self._initialize_session_from_character(character)

        session_doc = CharacterSessionDocumentDTO.model_validate(document)
        repaired_doc, changed = self._repair_session_from_persisted_actor_state(session_doc, character)
        if changed:
            repaired_doc.updated_at = datetime.now(UTC)
            await self.character_sessions.update_session(char_id, repaired_doc.model_dump(mode="json"))
        return repaired_doc

    async def _initialize_session_from_character(self, character: Character) -> CharacterSessionDocumentDTO:
        attributes = self._session_attributes_from_character(character)
        session_doc = CharacterSessionDocumentDTO(
            char_id=character.character_id,
            user_id=character.user_id,
            bio=CharacterSessionBioDTO(
                name=character.name,
                gender=cast("CharacterGender", character.gender),
                avatar=character.avatar_url,
                created_at=character.created_at or datetime.now(UTC),
            ),
            location=CharacterSessionLocationDTO(current=character.location_id or "52_52"),
            vitals=CharacterVitalsCalculator.build_vitals_from_snapshot(
                getattr(character, "vitals_snapshot", None),
                attributes,
            ),
            attributes=attributes,
            skills=self._session_skills_from_character(character),
            symbiote=CharacterSessionSymbioteDTO(
                name=character.symbiote.symbiote_name if character.symbiote else settings.default_symbiote_name,
                gift_rank=character.symbiote.gift_rank if character.symbiote else 1,
            ),
            updated_at=datetime.now(UTC),
        )
        await self.character_sessions.create_session(character.character_id, session_doc.model_dump(mode="json"))
        return session_doc

    @staticmethod
    def _session_attributes_from_character(character: Character) -> CharacterSessionAttributesDTO:
        attributes = getattr(character, "attributes", None)
        if attributes is None:
            return CharacterSessionAttributesDTO()

        return CharacterSessionAttributesDTO(
            strength=int(getattr(attributes, "strength", 8)),
            agility=int(getattr(attributes, "agility", 8)),
            endurance=int(getattr(attributes, "endurance", 8)),
            intellect=int(getattr(attributes, "intellect", 8)),
            memory=int(getattr(attributes, "memory", 8)),
            mental=int(getattr(attributes, "mental", 8)),
            perception=int(getattr(attributes, "perception", 8)),
            projection=int(getattr(attributes, "projection", 8)),
            prediction=int(getattr(attributes, "prediction", 8)),
        )

    @staticmethod
    def _session_skills_from_character(character: Character) -> dict[str, dict[str, object]]:
        skills = getattr(character, "skill_progress", None) or []
        session_skills: dict[str, dict[str, object]] = {}
        for skill in skills:
            if not getattr(skill, "is_unlocked", False):
                continue
            state = getattr(skill, "progress_state", None)
            session_skills[str(skill.skill_key)] = {
                "xp": float(getattr(skill, "total_xp", 0.0) or 0.0),
                "unlocked": True,
                "state": getattr(state, "value", state) or "PLUS",
            }
        return session_skills

    def _repair_session_from_persisted_actor_state(
        self,
        session_doc: CharacterSessionDocumentDTO,
        character: Character,
    ) -> tuple[CharacterSessionDocumentDTO, bool]:
        changed = False

        persisted_attributes = self._session_attributes_from_character(character)
        if not self._attributes_are_default(persisted_attributes) and self._attributes_are_default(
            session_doc.attributes
        ):
            session_doc.attributes = persisted_attributes
            changed = True

        persisted_skills = self._session_skills_from_character(character)
        if persisted_skills:
            merged_skills = dict(session_doc.skills)
            for skill_key, value in persisted_skills.items():
                if skill_key not in merged_skills:
                    merged_skills[skill_key] = value
                    changed = True
            session_doc.skills = merged_skills

        refreshed_vitals = CharacterVitalsCalculator.refresh_max_vitals(
            session_doc.vitals,
            session_doc.attributes,
            fill_if_default=True,
        )
        if refreshed_vitals != session_doc.vitals:
            session_doc.vitals = refreshed_vitals
            changed = True

        return session_doc, changed

    @staticmethod
    def _attributes_are_default(attributes: CharacterSessionAttributesDTO) -> bool:
        return all(value == 8 for value in attributes.model_dump(mode="json").values())
