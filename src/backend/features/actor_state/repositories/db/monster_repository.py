from uuid import UUID

from loguru import logger as log
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.features.actor_state.models import Monster


class MonsterRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_monsters_batch(self, monster_ids: list[str]) -> list[Monster]:
        log.debug(f"MonsterRepository | action=get_monsters_batch count={len(monster_ids)}")
        if not monster_ids:
            return []

        try:
            uuids = [UUID(monster_id) for monster_id in monster_ids]
        except ValueError:
            log.warning(
                f"MonsterRepository | action=get_monsters_batch status=failed reason=invalid_uuid ids='{monster_ids}'"
            )
            return []

        stmt = select(Monster).where(Monster.id.in_(uuids))
        try:
            result = await self.session.scalars(stmt)
            return list(result.all())
        except SQLAlchemyError as exc:
            log.exception(f"MonsterRepository | action=get_monsters_batch status=failed error={exc}")
            raise
