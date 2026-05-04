from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from loguru import logger

from src.backend.infrastructure.actor_state import CharacterRepository
from src.backend.infrastructure.actor_state.schemas.session import (
    CharacterGender,
    CharacterSessionAttributesDTO,
    CharacterSessionBioDTO,
    CharacterSessionDocumentDTO,
    CharacterSessionLocationDTO,
    CharacterSessionSymbioteDTO,
    CharacterSessionVitalsDTO,
)
from src.shared.schemas.character import CharacterStatusDTO

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.backend.infrastructure.actor_state.managers.session import CharacterSessionManager


class CharacterSessionService:
    """
    Manages active character sessions in Redis.
    Provides fallback to DB if session is missing and handles lazy regeneration.
    """

    def __init__(self, db_session: AsyncSession, session_manager: CharacterSessionManager):
        self.db_session = db_session
        self.session_manager = session_manager

    async def get_status(self, char_id: int) -> CharacterStatusDTO:
        """
        Main entry point for status polling.
        Returns status from Redis, or creates it from DB if missing.
        """
        session_data = await self.session_manager.get_session(char_id)
        
        if not session_data:
            logger.info("Session missing for char_id={}, attempting fallback to DB", char_id)
            session_doc = await self._initialize_session_from_db(char_id)
            if not session_doc:
                logger.error("Failed to recover session for char_id={}", char_id)
                from src.backend.core.exceptions import BusinessLogicException
                raise BusinessLogicException(f"Character session {char_id} not found")
        else:
            session_doc = CharacterSessionDocumentDTO.model_validate(session_data)

        # Apply lazy vitals regeneration
        updated_vitals = self._apply_vitals_regen(session_doc.vitals)
        
        # Sync back to Redis if changed
        if updated_vitals.last_update != session_doc.vitals.last_update:
            session_doc.vitals = updated_vitals
            session_doc.updated_at = datetime.now(UTC)
            await self.session_manager.update_session(char_id, session_doc.model_dump(mode="json"))

        return self._format_for_ui(session_doc)

    async def _initialize_session_from_db(self, char_id: int) -> CharacterSessionDocumentDTO | None:
        """
        Recovers session data from the database.
        """
        repo = CharacterRepository(self.db_session)
        character = await repo.get_by_id(char_id)
        
        if not character:
            return None

        # Build DTO from DB models
        doc = CharacterSessionDocumentDTO(
            char_id=char_id,
            user_id=character.user_id,
            bio=CharacterSessionBioDTO(
                name=character.name,
                gender=cast(CharacterGender, character.gender),
                avatar=character.avatar_url,
                created_at=character.created_at or datetime.now(UTC),
            ),
            location=CharacterSessionLocationDTO(current=character.location_id or "52_52"),
            attributes=CharacterSessionAttributesDTO(), # TODO: Load from character.attributes
            symbiote=CharacterSessionSymbioteDTO(
                name=character.symbiote.symbiote_name if character.symbiote else "Symbiote",
                gift_rank=character.symbiote.gift_rank if character.symbiote else 1,
            ),
            updated_at=datetime.now(UTC),
        )
        
        await self.session_manager.create_session(char_id, doc.model_dump(mode="json"))
        return doc

    def _apply_vitals_regen(self, vitals: CharacterSessionVitalsDTO) -> CharacterSessionVitalsDTO:
        now = datetime.now(UTC).timestamp()
        if vitals.last_update <= 0:
            vitals.last_update = now
            return vitals
            
        elapsed = now - vitals.last_update
        if elapsed < 1.0:
            return vitals
            
        # Update HP/Energy/Stamina if regen > 0
        for attr_name in ("hp", "energy", "stamina"):
            val = getattr(vitals, attr_name)
            if val.cur < val.max and val.regen > 0:
                regen_amount = val.regen * elapsed
                val.cur = min(val.max, int(val.cur + regen_amount))
            
        vitals.last_update = now
        return vitals

    def _format_for_ui(self, doc: CharacterSessionDocumentDTO) -> CharacterStatusDTO:
        """
        Converts DTO to the flat structure expected by the frontend templates.
        """
        return CharacterStatusDTO(
            character_id=doc.char_id,
            name=doc.bio.name,
            avatar_url=doc.bio.avatar,
            hp=float(doc.vitals.hp.cur),
            max_hp=doc.vitals.hp.max,
            energy=float(doc.vitals.energy.cur),
            max_energy=doc.vitals.energy.max,
            stamina=float(doc.vitals.stamina.cur),
            max_stamina=doc.vitals.stamina.max,
            last_update=datetime.fromtimestamp(doc.vitals.last_update, UTC),
        )
