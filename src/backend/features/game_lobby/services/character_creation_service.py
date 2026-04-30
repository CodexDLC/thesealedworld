from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import delete, func, select

from src.backend.core.exceptions import BusinessLogicException
from src.backend.infrastructure.db.actor_state.models import (
    Character,
    CharacterAttributes,
    CharacterSymbiote,
    ResourceWallet,
)
from src.backend.infrastructure.redis.character_session_schema import (
    CharacterSessionAttributesDTO,
    CharacterSessionBioDTO,
    CharacterSessionDocumentDTO,
    CharacterSessionLocationDTO,
    CharacterSessionSymbioteDTO,
)
from src.shared.enums import CoreDomain

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.backend.features.auth.models import User
    from src.backend.features.scenario.services import ScenarioService
    from src.backend.infrastructure.redis.character_session_manager import CharacterSessionManager
    from src.shared.schemas import CreateCharacterRequestDTO, ScenarioPayloadDTO


class CharacterCreationService:
    MAX_SLOTS = 4
    INITIAL_LOCATION_ID = "52_52"

    def __init__(
        self,
        db_session: AsyncSession,
        character_sessions: CharacterSessionManager,
        scenario_service: ScenarioService,
    ) -> None:
        self.db_session = db_session
        self.character_sessions = character_sessions
        self.scenario_service = scenario_service

    async def create_and_enter(
        self,
        user: User,
        dto: CreateCharacterRequestDTO,
    ) -> ScenarioPayloadDTO:
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
            state=CoreDomain.LOBBY,
            prev_state=None,
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

        try:
            await self.character_sessions.create_session(char_id, session_payload)
            payload = await self.scenario_service.initialize(char_id, "awakening_rift", source="onboarding")
        except Exception:
            await self.db_session.rollback()
            with suppress(Exception):
                await self.scenario_service.sessions.delete(char_id)
            with suppress(Exception):
                await self.scenario_service.repo.delete_state(char_id)
            with suppress(Exception):
                await self.character_sessions.delete_session(char_id)
            await self.db_session.execute(delete(Character).where(Character.character_id == char_id))
            await self.db_session.commit()
            raise

        payload.extra_data = {
            **(getattr(payload, "extra_data", None) or {}),
            "char_id": char_id,
            "quest_key": "awakening_rift",
        }
        character.game_stage = "scenario"
        character.prev_game_stage = "lobby"
        await self.db_session.commit()
        return payload

    async def _ensure_slot_available(self, user: User) -> None:
        count_stmt = select(func.count()).select_from(Character).where(Character.user_id == user.id)
        characters_count = await self.db_session.scalar(count_stmt)
        if int(characters_count or 0) >= self.MAX_SLOTS:
            raise BusinessLogicException("Character slot limit reached")
