import uuid

from loguru import logger as log
from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.shared.schemas.character import CharacterReadDTO

from ..models import Character


class CharacterRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def count_by_user_id(self, user_id: uuid.UUID) -> int:
        log.debug(f"CharacterRepository | action=count_by_user_id user_id={user_id}")
        stmt = select(func.count()).select_from(Character).where(Character.user_id == user_id)
        result = await self.session.scalar(stmt)
        return int(result or 0)

    async def save(self, character: Character) -> Character:
        log.debug(f"CharacterRepository | action=save character={character.name}")
        self.session.add(character)
        await self.session.flush()
        return character

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[Character]:
        log.debug(f"CharacterRepository | action=get_by_user_id user_id={user_id}")
        stmt = (
            select(Character).where(Character.user_id == user_id).order_by(Character.created_at, Character.character_id)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_by_id(self, character_id: int) -> Character | None:
        log.debug(f"CharacterRepository | action=get_by_id char_id={character_id}")
        stmt = select(Character).where(Character.character_id == character_id)
        return await self.session.scalar(stmt)

    async def get_by_id_and_user_id(self, character_id: int, user_id: uuid.UUID) -> Character | None:
        log.debug(f"CharacterRepository | action=get_by_id_and_user_id char_id={character_id} user_id={user_id}")
        stmt = (
            select(Character)
            .options(
                selectinload(Character.attributes),
                selectinload(Character.skill_progress),
                selectinload(Character.symbiote),
            )
            .where(Character.character_id == character_id, Character.user_id == user_id)
        )
        return await self.session.scalar(stmt)

    async def delete(self, character_id: int) -> None:
        log.warning(f"CharacterRepository | action=delete char_id={character_id}")
        await self.session.execute(delete(Character).where(Character.character_id == character_id))

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
