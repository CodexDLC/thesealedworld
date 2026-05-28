from loguru import logger as log
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.config.settings import settings
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

    async def upsert_from_session(self, char_id: int, symbiote: dict) -> None:
        payload = {
            "character_id": char_id,
            "symbiote_name": str(symbiote.get("name") or settings.default_symbiote_name),
            "gift_id": symbiote.get("gift_id"),
            "gift_xp": int(symbiote.get("gift_xp") or 0),
            "gift_rank": int(symbiote.get("gift_rank") or 1),
        }
        stmt = insert(CharacterSymbiote).values(**payload)
        stmt = stmt.on_conflict_do_update(
            index_elements=[CharacterSymbiote.character_id],
            set_={
                "symbiote_name": stmt.excluded.symbiote_name,
                "gift_id": stmt.excluded.gift_id,
                "gift_xp": stmt.excluded.gift_xp,
                "gift_rank": stmt.excluded.gift_rank,
            },
        )
        await self.session.execute(stmt)
