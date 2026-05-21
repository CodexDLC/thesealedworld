from loguru import logger as log
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.features.character.models import CharacterAttributes
from src.shared.schemas.character import CharacterAttributesReadDTO

ATTRIBUTE_KEYS = (
    "strength",
    "agility",
    "endurance",
    "intellect",
    "memory",
    "mental",
    "perception",
    "projection",
    "prediction",
)


class CharacterAttributesRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_attributes(self, char_id: int, attributes: dict[str, int]) -> None:
        row = {"character_id": char_id, **{key: int(attributes[key]) for key in ATTRIBUTE_KEYS}}
        stmt = insert(CharacterAttributes).values(row)
        stmt = stmt.on_conflict_do_update(
            index_elements=[CharacterAttributes.character_id],
            set_={key: row[key] for key in ATTRIBUTE_KEYS},
        )
        await self.session.execute(stmt)

    async def get_attributes_batch(self, char_ids: list[int]) -> list[CharacterAttributesReadDTO]:
        log.bind(char_id_count=len(char_ids)).debug("CharacterAttributesRepositoryGetAttributesBatch")
        if not char_ids:
            return []

        stmt = select(CharacterAttributes).where(CharacterAttributes.character_id.in_(char_ids))
        try:
            result = await self.session.scalars(stmt)
            return [CharacterAttributesReadDTO.model_validate(attributes) for attributes in result.all()]
        except SQLAlchemyError:
            log.exception("CharacterAttributesRepositoryGetAttributesBatchFailed")
            raise
