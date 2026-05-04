from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.features.scenario.services import ScenarioService
from src.backend.features_site.auth.models import User
from src.backend.infrastructure.actor_state import (
    CharacterRepository,
    CharacterSessionManager,
)
from src.shared.schemas import (
    GameLobbyPayloadDTO,
    LobbySlotDTO,
)


class GameLobbyService:
    MAX_SLOTS = 4

    async def get_start_payload(self, user: User, db_session: AsyncSession) -> GameLobbyPayloadDTO:
        repo = CharacterRepository(db_session)
        characters = await repo.get_by_user_id(user.id)

        occupied_count = len(characters)
        logger.info("Lobby payload built: user_id={} occupied_slots={}", user.id, occupied_count)

        occupied_slots = [
            LobbySlotDTO(
                index=index,
                is_empty=False,
                character_id=str(character.character_id),
                name=character.name,
                avatar_url=character.avatar_url,
                status=character.game_stage,
            )
            for index, character in enumerate(characters, start=1)
        ]

        # Fill remaining slots up to MAX_SLOTS
        empty_slots = []
        for index in range(occupied_count + 1, self.MAX_SLOTS + 1):
            empty_slots.append(LobbySlotDTO(index=index, is_empty=True, status="VACANT"))

        return GameLobbyPayloadDTO(
            can_start=occupied_count < self.MAX_SLOTS,
            slots=[*occupied_slots, *empty_slots],
            max_slots=self.MAX_SLOTS,
        )

    async def delete_character(
        self,
        user: User,
        character_id: int,
        db_session: AsyncSession,
        character_sessions: CharacterSessionManager,
        scenario_service: ScenarioService,
    ) -> None:
        repo = CharacterRepository(db_session)
        character = await self._get_owned_character_or_raise(db_session, user, character_id)
        char_id = character.character_id

        await scenario_service.integrator.sessions.delete(char_id)
        await scenario_service.integrator.repo.delete_state(char_id)
        await character_sessions.delete_session(char_id)
        await repo.delete(char_id)
        await db_session.commit()

    async def _get_owned_character_or_raise(self, db_session: AsyncSession, user: User, character_id: int):
        from src.backend.core.exceptions import BusinessLogicException

        repo = CharacterRepository(db_session)
        character = await repo.get_by_id_and_user_id(character_id, user.id)
        if character is None:
            raise BusinessLogicException("Character is unavailable")
        return character
