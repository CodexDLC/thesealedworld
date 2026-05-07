from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import select, update

from src.backend.infrastructure.arena.models import ArenaSeason

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ArenaSeasonRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def current(self, *, now: dt.datetime | None = None) -> ArenaSeason | None:
        now = now or dt.datetime.now(dt.UTC)
        result = await self.session.execute(
            select(ArenaSeason)
            .where(ArenaSeason.status == "active", ArenaSeason.started_at <= now, ArenaSeason.ends_at > now)
            .order_by(ArenaSeason.started_at.desc())
        )
        return result.scalar_one_or_none()

    async def get(self, season_id: int) -> ArenaSeason | None:
        result = await self.session.execute(select(ArenaSeason).where(ArenaSeason.id == season_id))
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        name: str,
        started_at: dt.datetime,
        ends_at: dt.datetime,
        status: str = "active",
    ) -> ArenaSeason:
        season = ArenaSeason(name=name, started_at=started_at, ends_at=ends_at, status=status)
        self.session.add(season)
        await self.session.flush()
        return season

    async def mark_ended(self, season_id: int) -> None:
        await self.session.execute(update(ArenaSeason).where(ArenaSeason.id == season_id).values(status="ended"))
        await self.session.flush()
