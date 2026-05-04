from loguru import logger as log
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.schemas.character import CharacterAttributesReadDTO

from ..models import CharacterAttributes


class CharacterAttributesRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_attributes_batch(self, char_ids: list[int]) -> list[CharacterAttributesReadDTO]:
        log.debug(f"CharacterAttributesRepository | action=get_attributes_batch count={len(char_ids)}")
        if not char_ids:
            return []

        stmt = select(CharacterAttributes).where(CharacterAttributes.character_id.in_(char_ids))
        try:
            result = await self.session.scalars(stmt)
            return [CharacterAttributesReadDTO.model_validate(attributes) for attributes in result.all()]
        except SQLAlchemyError as exc:
            log.exception(f"CharacterAttributesRepository | action=get_attributes_batch status=failed error={exc}")
            raise
