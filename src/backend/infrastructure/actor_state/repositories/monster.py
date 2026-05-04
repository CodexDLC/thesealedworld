import uuid
from collections.abc import Sequence
from typing import Any

from loguru import logger as log
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Monster


class MonsterRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, monster_id: uuid.UUID) -> Monster | None:
        log.debug(f"MonsterRepository | action=get_by_id monster_id={monster_id}")
        stmt = select(Monster).where(Monster.id == monster_id)
        return await self.session.scalar(stmt)

    async def get_all(self) -> list[Monster]:
        log.debug("MonsterRepository | action=get_all")
        stmt = select(Monster)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_monsters_batch(self, monster_ids: Sequence[uuid.UUID | str]) -> list[Monster]:
        log.debug(f"MonsterRepository | action=get_monsters_batch count={len(monster_ids)}")

        valid_ids = [m for m in monster_ids if isinstance(m, uuid.UUID) or self._is_valid_uuid(m)]
        if not valid_ids:
            return []

        stmt = select(Monster).where(Monster.id.in_(valid_ids)).options(selectinload(Monster.clan))
        result = await self.session.scalars(stmt)
        return list(result.all())

    def _is_valid_uuid(self, s: Any) -> bool:
        try:
            uuid.UUID(str(s))
            return True
        except (ValueError, TypeError):
            return False
