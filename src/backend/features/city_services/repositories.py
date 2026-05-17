from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from src.backend.features.city_services.models import CharacterTavernRoom

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class TavernRoomRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_for_character(self, *, character_id: int, tavern_id: str) -> CharacterTavernRoom | None:
        stmt = select(CharacterTavernRoom).where(
            CharacterTavernRoom.character_id == character_id,
            CharacterTavernRoom.tavern_id == tavern_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def grant_room(
        self,
        *,
        character_id: int,
        tavern_id: str,
        room_key: str,
    ) -> tuple[CharacterTavernRoom, bool]:
        existing = await self.get_for_character(character_id=character_id, tavern_id=tavern_id)
        if existing is not None:
            return existing, False

        room = CharacterTavernRoom(
            character_id=character_id,
            tavern_id=tavern_id,
            room_key=room_key,
            status="active",
        )
        self.session.add(room)
        await self.session.flush()
        return room, True
