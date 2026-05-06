from loguru import logger as log
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.features.character.models import CharacterSymbiote


class SymbioteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_character_id(self, char_id: int) -> CharacterSymbiote | None:
        log.debug(f"SymbioteRepository | action=get_by_character_id char_id={char_id}")
        stmt = select(CharacterSymbiote).where(CharacterSymbiote.character_id == char_id)
        return await self.session.scalar(stmt)

    async def get_symbiotes_batch(self, char_ids: list[int]) -> list[CharacterSymbiote]:
        log.debug(f"SymbioteRepository | action=get_symbiotes_batch count={len(char_ids)}")
        if not char_ids:
            return []
        stmt = select(CharacterSymbiote).where(CharacterSymbiote.character_id.in_(char_ids))
        result = await self.session.scalars(stmt)
        return list(result.all())
