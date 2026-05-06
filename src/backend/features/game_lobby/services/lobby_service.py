from loguru import logger

from src.backend.features.game_lobby.integrations import GameLobbyIntegration
from src.backend.features_site.auth.models import User
from src.shared.schemas import (
    GameLobbyPayloadDTO,
    LobbySlotDTO,
)


class GameLobbyService:
    MAX_SLOTS = 4

    def __init__(self, integration: GameLobbyIntegration) -> None:
        self.integration = integration

    async def get_start_payload(self, user: User) -> GameLobbyPayloadDTO:
        characters = await self.integration.list_user_characters(user.id)

        occupied_count = len(characters)
        logger.info("Lobby payload built: user_id={} occupied_slots={}", user.id, occupied_count)

        occupied_slots = [
            LobbySlotDTO(
                index=index,
                is_empty=False,
                character_id=str(character.character_id),
                name=character.name,
                avatar_url=character.avatar_url,
                status=character.status,
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
    ) -> None:
        await self.integration.delete_owned_character(user_id=user.id, character_id=character_id)
