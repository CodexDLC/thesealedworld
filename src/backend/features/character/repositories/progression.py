from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.backend.features.character.models import CharacterProgression


class CharacterProgressionRepository:
    def __init__(self, session) -> None:
        self.session = session

    async def get_by_character_id(self, char_id: int) -> CharacterProgression | None:
        result = await self.session.execute(
            select(CharacterProgression).where(CharacterProgression.character_id == char_id)
        )
        return result.scalar_one_or_none()

    async def ensure(self, char_id: int) -> CharacterProgression:
        progression = await self.get_by_character_id(char_id)
        if progression is not None:
            return progression
        progression = CharacterProgression(character_id=char_id, free_xp=0.0, metadata_={})
        self.session.add(progression)
        await self.session.flush()
        return progression

    async def increment_free_xp(self, char_id: int, delta: float) -> None:
        if delta <= 0:
            return
        stmt = insert(CharacterProgression).values(
            character_id=char_id,
            free_xp=round(float(delta), 4),
            metadata_={},
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[CharacterProgression.character_id],
            set_={"free_xp": CharacterProgression.free_xp + stmt.excluded.free_xp},
        )
        await self.session.execute(stmt)

    async def set_free_xp(self, char_id: int, value: float) -> None:
        stmt = insert(CharacterProgression).values(
            character_id=char_id,
            free_xp=round(float(value or 0.0), 4),
            metadata_={},
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[CharacterProgression.character_id],
            set_={"free_xp": stmt.excluded.free_xp},
        )
        await self.session.execute(stmt)
