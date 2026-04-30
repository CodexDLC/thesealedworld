from loguru import logger as log
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.infrastructure.db.actor_state.models import Character, CharacterAttributes
from src.shared.schemas.character import CharacterAttributesReadDTO, CharacterReadDTO


class CharacterRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_characters_batch(self, char_ids: list[int]) -> list[CharacterReadDTO]:
        log.debug(f"CharacterRepository | action=get_characters_batch count={len(char_ids)}")
        if not char_ids:
            return []

        stmt = select(Character).where(Character.character_id.in_(char_ids))
        try:
            result = await self.session.scalars(stmt)
            return [CharacterReadDTO.model_validate(character) for character in result.all()]
        except SQLAlchemyError as exc:
            log.exception(f"CharacterRepository | action=get_characters_batch status=failed error={exc}")
            raise


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


CharactersRepoORM = CharacterRepository
CharacterAttributesRepoORM = CharacterAttributesRepository
