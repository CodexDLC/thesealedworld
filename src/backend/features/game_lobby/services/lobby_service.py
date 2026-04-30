from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.features.auth.models import User
from src.backend.infrastructure.db.actor_state.models import Character
from src.shared.schemas import GameLobbyPayloadDTO, LobbySlotDTO


class GameLobbyService:
    MAX_SLOTS = 4

    async def get_start_payload(self, user: User, db_session: AsyncSession) -> GameLobbyPayloadDTO:
        # Fetch only characters for the current user
        stmt = (
            select(Character).where(Character.user_id == user.id).order_by(Character.created_at, Character.character_id)
        )
        result = await db_session.scalars(stmt)
        characters = list(result.all())

        occupied_count = len(characters)

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

        # Fill remaining slots up to MAX_SLOTS
        empty_slots = []
        for index in range(occupied_count + 1, self.MAX_SLOTS + 1):
            empty_slots.append(LobbySlotDTO(index=index, is_empty=True, status="VACANT"))

        return GameLobbyPayloadDTO(
            can_start=occupied_count < self.MAX_SLOTS,
            slots=[*occupied_slots, *empty_slots],
            max_slots=self.MAX_SLOTS,
        )
