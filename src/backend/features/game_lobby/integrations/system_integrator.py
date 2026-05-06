from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from loguru import logger

from src.backend.core.exceptions import BusinessLogicException
from src.backend.features.character.repositories import CharacterRepository
from src.backend.features.character.schemas.session import (
    CharacterGender,
    CharacterSessionAttributesDTO,
    CharacterSessionBioDTO,
    CharacterSessionDocumentDTO,
    CharacterSessionLocationDTO,
    CharacterSessionSymbioteDTO,
)
from src.shared.enums import CoreDomain

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.backend.features.character.managers import CharacterSessionManager
    from src.backend.features.scenario.services import ScenarioService
    from src.shared.schemas import ScenarioPayloadDTO


@dataclass(frozen=True, slots=True)
class LobbyCharacterSummary:
    character_id: int
    name: str
    avatar_url: str | None
    status: str


@dataclass(frozen=True, slots=True)
class CreatedLobbyCharacter:
    character_id: int
    user_id: uuid.UUID
    name: str
    gender: CharacterGender
    avatar_url: str
    created_at: datetime
    location_id: str


class GameLobbyIntegration:
    def __init__(
        self,
        *,
        character_repo: CharacterRepository | None = None,
        db_session: AsyncSession | None = None,
        character_sessions: CharacterSessionManager,
        scenario_service: ScenarioService,
    ) -> None:
        if character_repo is None:
            if db_session is None:
                raise ValueError("character_repo or db_session is required")
            character_repo = CharacterRepository(db_session)
        self.character_repo = character_repo
        self.character_sessions = character_sessions
        self.scenario_service = scenario_service

    def _characters(self) -> CharacterRepository:
        return self.character_repo

    async def list_user_characters(self, user_id: uuid.UUID) -> list[LobbyCharacterSummary]:
        characters = await self._characters().get_by_user_id(user_id)
        return [
            LobbyCharacterSummary(
                character_id=character.character_id,
                name=character.name,
                avatar_url=character.avatar_url,
                status=character.game_stage,
            )
            for character in characters
        ]

    async def count_user_characters(self, user_id: uuid.UUID) -> int:
        return await self._characters().count_by_user_id(user_id)

    async def create_character(
        self,
        *,
        user_id: uuid.UUID,
        name: str,
        gender: CharacterGender,
        avatar_url: str,
        game_stage: str,
        prev_game_stage: str,
        location_id: str,
    ) -> CreatedLobbyCharacter:
        created_at = datetime.now(UTC)
        character = await self._characters().create_with_defaults(
            user_id=user_id,
            name=name,
            gender=str(gender),
            avatar_url=avatar_url,
            game_stage=game_stage,
            prev_game_stage=prev_game_stage,
            location_id=location_id,
        )
        char_id = character.character_id
        await self._characters().commit()
        logger.info("Character persisted: char_id={} user_id={}", char_id, user_id)

        return CreatedLobbyCharacter(
            character_id=char_id,
            user_id=user_id,
            name=name,
            gender=gender,
            avatar_url=avatar_url,
            created_at=created_at,
            location_id=location_id,
        )

    async def create_active_session(self, character: CreatedLobbyCharacter) -> None:
        session_payload = CharacterSessionDocumentDTO(
            char_id=character.character_id,
            user_id=character.user_id,
            state=CoreDomain.LOBBY,
            prev_state=None,
            bio=CharacterSessionBioDTO(
                name=character.name,
                gender=character.gender,
                avatar=character.avatar_url,
                created_at=character.created_at,
            ),
            location=CharacterSessionLocationDTO(current=character.location_id),
            attributes=CharacterSessionAttributesDTO(),
            symbiote=CharacterSessionSymbioteDTO(),
            updated_at=datetime.now(UTC),
        ).model_dump(mode="json")

        await self.character_sessions.create_session(character.character_id, session_payload)

    async def initialize_starting_scenario(
        self,
        char_id: int,
        quest_key: str,
        *,
        source: str,
    ) -> ScenarioPayloadDTO:
        return await self.scenario_service.initialize(char_id, quest_key, source=source)

    async def cleanup_runtime(self, char_id: int) -> None:
        await self.scenario_service.cleanup(char_id)
        await self.character_sessions.delete_session(char_id)

    async def delete_owned_character(self, *, user_id: uuid.UUID, character_id: int) -> None:
        repo = self._characters()
        character = await repo.get_by_id_and_user_id(character_id, user_id)
        if character is None:
            raise BusinessLogicException("Character is unavailable")

        char_id = character.character_id
        await self.cleanup_runtime(char_id)
        await repo.delete(char_id)
        await repo.commit()

    async def cleanup_failed_character_creation(self, char_id: int) -> None:
        repo = self._characters()
        await repo.rollback()
        with suppress(Exception):
            await self.scenario_service.cleanup(char_id)
        with suppress(Exception):
            await self.character_sessions.delete_session(char_id)
        with suppress(Exception):
            await repo.delete(char_id)

        await repo.commit()

    async def mark_character_entered_scenario(self, char_id: int) -> None:
        updated = await self._characters().set_character_state(
            char_id,
            CoreDomain.SCENARIO.value,
            prev_game_stage=CoreDomain.LOBBY.value,
        )
        if not updated:
            raise BusinessLogicException("Character is unavailable")
        await self._characters().commit()
