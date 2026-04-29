from src.backend.features.auth.models import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.features.actor_state.models import Character
from src.backend.features.game_lobby.dto.lobby import GameLobbyPayloadDTO, LobbySlotDTO


class GameLobbyService:
    MAX_SLOTS = 4

    async def get_start_payload(self, user: User, db_session: AsyncSession) -> GameLobbyPayloadDTO:
        result = await db_session.scalars(
            select(Character).where(Character.user_id == user.id).order_by(Character.created_at, Character.character_id)
        )
        characters = list(result.all())
        occupied_slots = [
            LobbySlotDTO(
                index=index,
                is_empty=False,
                character_id=str(character.character_id),
                name=character.name,
                avatar_url=None,
                status=character.game_stage,
            )
            for index, character in enumerate(characters, start=1)
        ]
        empty_slots = [
            LobbySlotDTO(index=index)
            for index in range(len(occupied_slots) + 1, self.MAX_SLOTS + 1)
        ]
        return GameLobbyPayloadDTO(
            can_start=len(occupied_slots) < self.MAX_SLOTS,
            slots=[*occupied_slots, *empty_slots],
        )
