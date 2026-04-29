from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.exceptions import BusinessLogicException
from src.backend.core.redis.character_session_manager import CharacterSessionManager
from src.backend.core.redis.character_session_schema import (
    CharacterSessionAttributesDTO,
    CharacterSessionBioDTO,
    CharacterSessionDocumentDTO,
    CharacterSessionLocationDTO,
    CharacterSessionSymbioteDTO,
)
from src.backend.features.actor_state.models import Character, CharacterAttributes, CharacterSymbiote, ResourceWallet
from src.backend.features.auth.models import User
from src.backend.features.game_lobby.dto.creation import CreateCharacterRequestDTO, ScenarioPlaceholderPayloadDTO
from src.shared.enums import CoreDomain


class CharacterCreationService:
    MAX_SLOTS = 4
    INITIAL_LOCATION_ID = "52_52"

    def __init__(self, db_session: AsyncSession, character_sessions: CharacterSessionManager) -> None:
        self.db_session = db_session
        self.character_sessions = character_sessions

    async def create_and_enter(
        self,
        user: User,
        dto: CreateCharacterRequestDTO,
    ) -> ScenarioPlaceholderPayloadDTO:
        await self._ensure_slot_available(user)

        created_at = datetime.now(UTC)
        character = Character(
            user_id=user.id,
            name=dto.name,
            gender=dto.gender,
            game_stage="session_pending",
            prev_game_stage="LOBBY",
            location_id=self.INITIAL_LOCATION_ID,
        )
        character.attributes = CharacterAttributes()
        character.symbiote = CharacterSymbiote()
        character.wallet = ResourceWallet()

        self.db_session.add(character)
        await self.db_session.flush()
        char_id = character.character_id
        await self.db_session.commit()

        session_payload = CharacterSessionDocumentDTO(
            char_id=char_id,
            user_id=user.id,
            state=CoreDomain.SCENARIO,
            prev_state=CoreDomain.LOBBY,
            bio=CharacterSessionBioDTO(
                name=dto.name,
                gender=dto.gender,
                avatar=dto.avatar,
                created_at=created_at,
            ),
            location=CharacterSessionLocationDTO(current=self.INITIAL_LOCATION_ID),
            attributes=CharacterSessionAttributesDTO(),
            symbiote=CharacterSessionSymbioteDTO(),
            updated_at=datetime.now(UTC),
        ).model_dump(mode="json")

        await self.character_sessions.create_session(char_id, session_payload)

        await self.db_session.execute(
            update(Character)
            .where(Character.character_id == char_id)
            .values(game_stage="scenario", prev_game_stage="session_pending")
        )
        await self.db_session.commit()

        # TODO(scenario): publish "scenario.start_requested".
        #   payload: {char_id, quest_key: "awakening_rift", source: "onboarding"}
        #   Donor reference: temp/.../tutorial_handler.py.
        #   Return the resulting scenario payload here once scenario is wired.
        return ScenarioPlaceholderPayloadDTO()

    async def _ensure_slot_available(self, user: User) -> None:
        count_stmt = select(func.count()).select_from(Character).where(Character.user_id == user.id)
        characters_count = await self.db_session.scalar(count_stmt)
        if int(characters_count or 0) >= self.MAX_SLOTS:
            raise BusinessLogicException("Character slot limit reached")
