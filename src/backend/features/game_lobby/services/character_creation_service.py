from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from loguru import logger

from src.backend.core.exceptions import BusinessLogicException
from src.backend.infrastructure.actor_state.models import (
    Character,
    CharacterAttributes,
    CharacterSymbiote,
    ResourceWallet,
)
from src.backend.infrastructure.actor_state.repositories import CharacterRepository
from src.backend.infrastructure.actor_state.schemas.session import (
    CharacterSessionAttributesDTO,
    CharacterSessionBioDTO,
    CharacterSessionDocumentDTO,
    CharacterSessionLocationDTO,
    CharacterSessionSymbioteDTO,
)
from src.shared.enums import CoreDomain

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.backend.features.scenario.services import ScenarioService
    from src.backend.features_site.auth.models import User
    from src.backend.infrastructure.actor_state import CharacterSessionManager
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
        logger.info("Character creation started: user_id={}", user.id)
        await self._ensure_slot_available(user)

        repo = CharacterRepository(self.db_session)
        created_at = datetime.now(UTC)

        # Determine default avatar based on gender if none provided
        avatar_url = dto.avatar
        if not avatar_url:
            if dto.gender == "female":
                avatar_url = "/static/images/avatars/silhouette_f.png"
            else:
                avatar_url = "/static/images/avatars/silhouette_m.png"

        character = Character(
            user_id=user.id,
            name=dto.name,
            gender=dto.gender,
            avatar_url=avatar_url,
            game_stage="session_pending",
            prev_game_stage="LOBBY",
            location_id=self.INITIAL_LOCATION_ID,
        )
        character.attributes = CharacterAttributes()
        character.symbiote = CharacterSymbiote()
        character.wallet = ResourceWallet()

        await repo.save(character)
        char_id = character.character_id
        await self.db_session.commit()
        logger.info("Character persisted: char_id={} user_id={}", char_id, user.id)

        session_payload = CharacterSessionDocumentDTO(
            char_id=char_id,
            user_id=user.id,
            state=CoreDomain.LOBBY,
            prev_state=None,
            bio=CharacterSessionBioDTO(
                name=dto.name,
                gender=dto.gender,
                avatar=avatar_url,
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
            logger.exception("Character creation failed; cleanup started: char_id={} user_id={}", char_id, user.id)
            await self.db_session.rollback()
            with suppress(Exception):
                await self.scenario_service.integrator.sessions.delete(char_id)
            with suppress(Exception):
                await self.scenario_service.integrator.repo.delete_state(char_id)
            with suppress(Exception):
                await self.character_sessions.delete_session(char_id)

            await repo.delete(char_id)
            await self.db_session.commit()
            logger.warning("Character creation cleanup finished: char_id={} user_id={}", char_id, user.id)
            raise

        payload.extra_data = {
            **(getattr(payload, "extra_data", None) or {}),
            "char_id": char_id,
            "quest_key": "awakening_rift",
        }
        character.game_stage = "scenario"
        character.prev_game_stage = "lobby"
        await self.db_session.commit()
        logger.info("Character entered scenario: char_id={} user_id={}", char_id, user.id)
        return payload

    async def _ensure_slot_available(self, user: User) -> None:
        repo = CharacterRepository(self.db_session)
        characters_count = await repo.count_by_user_id(user.id)
        if characters_count >= self.MAX_SLOTS:
            logger.warning("Character creation rejected: slot_limit user_id={} count={}", user.id, characters_count)
            raise BusinessLogicException("Character slot limit reached")
