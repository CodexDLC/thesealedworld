from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from loguru import logger as log
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.backend.infrastructure.actor_state.models import GeneratedClanORM, GeneratedMonsterORM, Monster

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class MonsterGenerationRepository:
    """Persistence adapter for generated monster ownership."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_clan_by_unique_hash(self, unique_hash: str) -> GeneratedClanORM | None:
        stmt = (
            select(GeneratedClanORM)
            .where(GeneratedClanORM.unique_hash == unique_hash)
            .options(selectinload(GeneratedClanORM.members))
        )
        return await self.session.scalar(stmt)

    async def get_clans_by_context_hash(self, context_hash: str) -> list[GeneratedClanORM]:
        stmt = (
            select(GeneratedClanORM)
            .where(GeneratedClanORM.context_hash == context_hash)
            .options(selectinload(GeneratedClanORM.members))
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_clans_by_zone(self, zone_id: str) -> list[GeneratedClanORM]:
        stmt = (
            select(GeneratedClanORM)
            .where(GeneratedClanORM.zone_id == zone_id)
            .options(selectinload(GeneratedClanORM.members))
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_clan_members(self, clan_id: uuid.UUID | str) -> list[GeneratedMonsterORM]:
        stmt = (
            select(Monster)
            .where(Monster.clan_id == uuid.UUID(str(clan_id)))
            .order_by(Monster.threat_rating, Monster.role)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def create_clan_with_members(
        self,
        clan: GeneratedClanORM,
        members: Sequence[GeneratedMonsterORM],
    ) -> GeneratedClanORM:
        log.debug(
            "MonsterGenerationRepository | action=create_clan_with_members clan_id={} members={}",
            clan.id,
            len(members),
        )
        clan.members.extend(members)
        self.session.add(clan)
        self.session.add_all(list(members))
        await self.session.flush()
        return clan

    async def get_monsters_by_role_and_threat(
        self,
        role: str,
        min_threat: int,
        max_threat: int,
        limit: int = 5,
    ) -> list[GeneratedMonsterORM]:
        stmt = (
            select(Monster)
            .where(Monster.role == role, Monster.threat_rating >= min_threat, Monster.threat_rating <= max_threat)
            .order_by(Monster.threat_rating)
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())
