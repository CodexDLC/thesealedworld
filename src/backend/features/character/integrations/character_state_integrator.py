from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from pydantic import ValidationError

from src.backend.config.settings import settings
from src.backend.core.exceptions import BusinessLogicException
from src.backend.features.character.runtime import CharacterVitalsCalculator
from src.backend.features.character.runtime.gear_score import CharacterGearScoreCalculator
from src.backend.features.character.schemas.session import (
    CharacterSessionAttributesDTO,
    CharacterSessionBioDTO,
    CharacterSessionDocumentDTO,
    CharacterSessionItemsDTO,
    CharacterSessionLocationDTO,
    CharacterSessionPendingProgressDTO,
    CharacterSessionProgressionDTO,
    CharacterSessionRefsDTO,
    CharacterSessionRiskDTO,
    CharacterSessionSymbioteDTO,
)
from src.backend.features.inventory.repositories.items import runtime_item_from_instance
from src.backend.features.inventory.services.projection import build_active_character_projection, build_runtime_session
from src.shared.enums import CoreDomain
from src.shared.enums.skill_enums import SkillProgressState

if TYPE_CHECKING:
    from uuid import UUID

    from src.backend.features.character.managers.session import CharacterSessionManager
    from src.backend.features.character.models.character import Character
    from src.backend.features.character.repositories import (
        CharacterProgressionRepository,
        CharacterRepository,
        SkillRepository,
    )
    from src.backend.features.character.schemas.session import CharacterGender
    from src.backend.features.expedition import CharacterExpeditionRepository
    from src.backend.features.inventory.repositories.items import InventoryItemRepository


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
        progression_repo: CharacterProgressionRepository | None = None,
        expedition_repo: CharacterExpeditionRepository | None = None,
        inventory_repo: InventoryItemRepository | None = None,
        gear_score_calculator: CharacterGearScoreCalculator | None = None,
    ) -> None:
        self.character_sessions = character_sessions
        self.character_repo = character_repo
        self.skill_repo = skill_repo
        self.progression_repo = progression_repo
        self.expedition_repo = expedition_repo
        self.inventory_repo = inventory_repo
        self.gear_score_calculator = gear_score_calculator or CharacterGearScoreCalculator()

    async def get_actor_core(self, user_id: UUID, char_id: int) -> ActiveCharacterDocument:
        session_doc = await self._get_or_initialize_session_doc(user_id, char_id)
        session_doc = await self._apply_and_persist_vitals_regen(session_doc, char_id)
        return ActiveCharacterDocument(
            key=self.character_sessions.build_key(char_id),
            document=session_doc.model_dump(mode="json"),
        )

    async def get_status_document(self, user_id: UUID, char_id: int) -> dict[str, Any]:
        session_doc = await self._get_or_initialize_session_doc(user_id, char_id)
        session_doc = await self._apply_and_persist_vitals_regen(session_doc, char_id)
        return session_doc.model_dump(mode="json")

    async def bootstrap_active_session(self, user_id: UUID, char_id: int) -> CharacterSessionDocumentDTO:
        """Replace AC from cold character rows after lobby selection."""
        character = await self.character_repo.get_by_id_and_user_id(char_id, user_id)
        if character is None:
            raise BusinessLogicException("Character is unavailable")

        session_doc = await self._build_session_from_character(character)
        await self.character_sessions.replace_session(char_id, session_doc.model_dump(mode="json"))
        return session_doc

    async def update_avatar(self, char_id: int, avatar_url: str) -> None:
        await self.character_sessions.update_bio(char_id, avatar=avatar_url)

    async def unlock_skills(
        self,
        char_id: int,
        skill_keys: list[str],
        *,
        progress_state: SkillProgressState = SkillProgressState.PLUS,
        initial_xp: float = 0.0,
    ) -> None:
        await self.skill_repo.unlock_skills(
            char_id,
            skill_keys,
            progress_state=progress_state,
            initial_xp=initial_xp,
        )
        await self.character_sessions.unlock_skills(char_id, skill_keys, initial_xp=initial_xp)

    async def _get_or_initialize_session_doc(self, user_id: UUID, char_id: int) -> CharacterSessionDocumentDTO:
        character = await self.character_repo.get_by_id_and_user_id(char_id, user_id)
        if character is None:
            raise BusinessLogicException("Character is unavailable")

        document = await self.character_sessions.get_session(char_id)
        if document is None:
            return await self._initialize_session_from_character(character)

        try:
            session_doc = CharacterSessionDocumentDTO.model_validate(document)
        except ValidationError:
            session_doc = await self._build_session_from_character(character)
            await self.character_sessions.update_session(char_id, session_doc.model_dump(mode="json"))
            return session_doc
        repaired_doc, changed = self._repair_session_from_persisted_actor_state(session_doc, character)
        if changed:
            repaired_doc.updated_at = datetime.now(UTC)
            await self.character_sessions.update_session(char_id, repaired_doc.model_dump(mode="json"))
        return repaired_doc

    async def _initialize_session_from_character(self, character: Character) -> CharacterSessionDocumentDTO:
        session_doc = await self._build_session_from_character(character)
        await self.character_sessions.create_session(character.character_id, session_doc.model_dump(mode="json"))
        return session_doc

    async def _build_session_from_character(self, character: Character) -> CharacterSessionDocumentDTO:
        attributes = self._session_attributes_from_character(character)
        expedition = (
            await self.expedition_repo.get_active_for_character(character.character_id)
            if self.expedition_repo
            else None
        )
        progression = (
            await self.progression_repo.get_by_character_id(character.character_id) if self.progression_repo else None
        )
        pending = dict(getattr(expedition, "pending_progress_json", None) or {})
        session_doc = CharacterSessionDocumentDTO(
            char_id=character.character_id,
            user_id=character.user_id,
            bio=CharacterSessionBioDTO(
                name=character.name,
                gender=cast("CharacterGender", character.gender),
                avatar=character.avatar_url,
                created_at=character.created_at or datetime.now(UTC),
            ),
            state=CoreDomain.DEATH
            if getattr(expedition, "status", None) == "death_pending"
            else self._core_domain(getattr(character, "game_stage", None)),
            prev_state=self._core_domain(getattr(character, "prev_game_stage", None), fallback=CoreDomain.LOBBY),
            location=CharacterSessionLocationDTO(
                current=(expedition.current_location_id if expedition else getattr(character, "location_id", None))
                or "52_52",
                prev=getattr(character, "prev_location_id", None),
            ),
            vitals=CharacterVitalsCalculator.build_vitals_from_snapshot(
                getattr(character, "vitals_snapshot", None),
                attributes,
            ),
            attributes=attributes,
            sessions=self._session_refs_from_character(character),
            active_quest=self._active_quest_from_character(character),
            skills=self._session_skills_from_character(character),
            progression=CharacterSessionProgressionDTO(
                free_xp=float(getattr(progression, "free_xp", 0.0) or 0.0),
            ),
            pending_progress=CharacterSessionPendingProgressDTO.model_validate(
                {
                    "free_xp": pending.get("free_xp", 0.0),
                    "skills": pending.get("skills", {}),
                    "weapon": pending.get("weapon", {}),
                    "armor": pending.get("armor", {}),
                    "symbiote": pending.get("symbiote", {}),
                }
            ),
            risk=CharacterSessionRiskDTO(
                sync_state="death"
                if getattr(expedition, "status", None) == "death_pending"
                else "unsafe"
                if expedition
                else "safe",
                system_connect=not bool(expedition),
                run_id=getattr(expedition, "run_id", None),
                corpse_id=getattr(expedition, "corpse_id", None),
                pending_free_xp=float(pending.get("free_xp", 0.0) or 0.0),
                pending_skill_count=len(pending.get("skills") or {}),
            ),
            symbiote=CharacterSessionSymbioteDTO(
                name=character.symbiote.symbiote_name if character.symbiote else settings.default_symbiote_name,
                gift_rank=character.symbiote.gift_rank if character.symbiote else 1,
            ),
            updated_at=datetime.now(UTC),
        )
        await self._hydrate_items_and_gear_score(session_doc, expedition_run_id=getattr(expedition, "run_id", None))
        return session_doc

    @staticmethod
    def _session_refs_from_character(character: Character) -> CharacterSessionRefsDTO:
        active_sessions = getattr(character, "active_sessions", None)
        if not isinstance(active_sessions, dict):
            return CharacterSessionRefsDTO()
        return CharacterSessionRefsDTO.model_validate(active_sessions)

    @staticmethod
    def _active_quest_from_character(character: Character) -> str | None:
        active_sessions = getattr(character, "active_sessions", None)
        if not isinstance(active_sessions, dict):
            return None
        active_quest = active_sessions.get("active_quest")
        return str(active_quest) if active_quest else None

    async def _hydrate_items_and_gear_score(
        self,
        session_doc: CharacterSessionDocumentDTO,
        *,
        expedition_run_id: str | None = None,
    ) -> None:
        if self.inventory_repo is None:
            return

        rows = await self.inventory_repo.list_character_items(
            session_doc.char_id,
            expedition_run_id=expedition_run_id,
        )
        if not rows:
            return

        runtime_items = [runtime_item_from_instance(instance, placement) for instance, placement in rows]
        inventory_session = build_runtime_session(session_doc.char_id, runtime_items)
        projection = build_active_character_projection(inventory_session).model_dump(mode="json")
        session_doc.items = CharacterSessionItemsDTO.model_validate(projection)
        session_doc.metrics.gear_score = self.gear_score_calculator.calculate_from_active_character(
            session_doc.model_dump(mode="json")
        )

    async def _apply_and_persist_vitals_regen(
        self,
        session_doc: CharacterSessionDocumentDTO,
        char_id: int,
    ) -> CharacterSessionDocumentDTO:
        before = session_doc.vitals.model_dump(mode="json")
        updated_vitals = CharacterVitalsCalculator.apply_regen(session_doc.vitals)
        if updated_vitals.model_dump(mode="json") != before:
            session_doc.vitals = updated_vitals
            session_doc.updated_at = datetime.now(UTC)
            await self.character_sessions.update_session(char_id, session_doc.model_dump(mode="json"))
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

    @staticmethod
    def _core_domain(value: Any, *, fallback: CoreDomain = CoreDomain.EXPLORATION) -> CoreDomain:
        try:
            return CoreDomain(str(value))
        except (TypeError, ValueError):
            return fallback
