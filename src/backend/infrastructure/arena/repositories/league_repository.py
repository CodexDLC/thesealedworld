from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import or_, select

from src.backend.infrastructure.arena.models import ArenaLeague

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ArenaLeagueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_season(self, season_id: int | None = None) -> list[ArenaLeague]:
        stmt = select(ArenaLeague)
        if season_id is None:
            stmt = stmt.where(ArenaLeague.season_id.is_(None))
        else:
            stmt = stmt.where(or_(ArenaLeague.season_id == season_id, ArenaLeague.season_id.is_(None)))
        result = await self.session.execute(stmt.order_by(ArenaLeague.tier.asc()))
        return list(result.scalars().all())

    async def resolve_for_rating(self, rating: int, *, season_id: int | None = None) -> ArenaLeague | None:
        leagues = await self.list_for_season(season_id)
        season_specific = [league for league in leagues if league.season_id == season_id]
        candidates = season_specific or [league for league in leagues if league.season_id is None]
        for league in candidates:
            if rating >= league.min_rating and (league.max_rating is None or rating <= league.max_rating):
                return league
        return candidates[-1] if candidates else None
