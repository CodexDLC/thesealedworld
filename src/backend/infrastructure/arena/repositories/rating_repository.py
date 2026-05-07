from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.backend.infrastructure.arena.models import ArenaRating

if TYPE_CHECKING:
    import datetime as dt

    from sqlalchemy.ext.asyncio import AsyncSession


class ArenaRatingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(
        self,
        *,
        entity_type: str,
        entity_id: int,
        mode_size: int,
        season_id: int,
    ) -> ArenaRating | None:
        result = await self.session.execute(
            select(ArenaRating).where(
                ArenaRating.entity_type == entity_type,
                ArenaRating.entity_id == entity_id,
                ArenaRating.mode_size == mode_size,
                ArenaRating.season_id == season_id,
            )
        )
        return result.scalar_one_or_none()

    async def ensure(
        self,
        *,
        entity_type: str,
        entity_id: int,
        mode_size: int,
        season_id: int,
        rating: int = 1000,
        league_tier: int = 1,
        placement_left: int = 5,
    ) -> ArenaRating:
        existing = await self.get(
            entity_type=entity_type,
            entity_id=entity_id,
            mode_size=mode_size,
            season_id=season_id,
        )
        if existing is not None:
            return existing
        row = ArenaRating(
            entity_type=entity_type,
            entity_id=entity_id,
            mode_size=mode_size,
            season_id=season_id,
            rating=rating,
            peak_rating=rating,
            league_tier=league_tier,
            placement_left=placement_left,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def leaderboard(
        self,
        *,
        season_id: int,
        mode_size: int,
        entity_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ArenaRating]:
        stmt = select(ArenaRating).where(ArenaRating.season_id == season_id, ArenaRating.mode_size == mode_size)
        if entity_type is not None:
            stmt = stmt.where(ArenaRating.entity_type == entity_type)
        stmt = stmt.order_by(ArenaRating.rating.desc(), ArenaRating.peak_rating.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def record_result(
        self,
        rating: ArenaRating,
        *,
        rating_after: int,
        league_tier: int,
        score: float,
        played_at: dt.datetime,
    ) -> ArenaRating:
        rating.rating = rating_after
        rating.peak_rating = max(rating.peak_rating, rating_after)
        rating.league_tier = league_tier
        rating.matches_played += 1
        rating.placement_left = max(0, rating.placement_left - 1)
        rating.last_match_at = played_at
        if score > 0.5:
            rating.wins += 1
        elif score < 0.5:
            rating.losses += 1
        else:
            rating.draws += 1
        await self.session.flush()
        return rating

    async def upsert_seed(self, values: dict) -> None:
        stmt = insert(ArenaRating).values(**values)
        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_arena_ratings_entity_mode_season",
        )
        await self.session.execute(stmt)
