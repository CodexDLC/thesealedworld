from loguru import logger as log
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.features.character.models import CharacterSymbiote


class SymbioteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_character_id(self, char_id: int) -> CharacterSymbiote | None:
        log.bind(char_id=char_id).debug("SymbioteRepositoryGetByCharacterId")
        stmt = select(CharacterSymbiote).where(CharacterSymbiote.character_id == char_id)
        return await self.session.scalar(stmt)

    async def get_symbiotes_batch(self, char_ids: list[int]) -> list[CharacterSymbiote]:
        log.bind(char_id_count=len(char_ids)).debug("SymbioteRepositoryGetSymbiotesBatch")
        if not char_ids:
            return []
        stmt = select(CharacterSymbiote).where(CharacterSymbiote.character_id.in_(char_ids))
        result = await self.session.scalars(stmt)
        return list(result.all())
