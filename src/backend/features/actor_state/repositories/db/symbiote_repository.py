from loguru import logger as log
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.features.actor_state.models import CharacterSymbiote


class SymbioteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_symbiotes_batch(self, char_ids: list[int]) -> list[CharacterSymbiote]:
        log.debug(f"SymbioteRepository | action=get_symbiotes_batch count={len(char_ids)}")
        if not char_ids:
            return []

        stmt = select(CharacterSymbiote).where(CharacterSymbiote.character_id.in_(char_ids))
        try:
            result = await self.session.scalars(stmt)
            return list(result.all())
        except SQLAlchemyError as exc:
            log.exception(f"SymbioteRepository | action=get_symbiotes_batch status=failed error={exc}")
            raise


SymbioteRepoORM = SymbioteRepository
