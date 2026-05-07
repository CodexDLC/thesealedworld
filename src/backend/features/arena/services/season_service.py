from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from src.backend.features.arena.dto.season import SeasonDTO

if TYPE_CHECKING:
    from src.backend.infrastructure.arena.models import ArenaSeason
    from src.backend.infrastructure.arena.repositories import ArenaSeasonRepository


class SeasonService:
    SEASON_MONTHS = 3

    def __init__(self, *, seasons: ArenaSeasonRepository) -> None:
        self.seasons = seasons

    async def current_season(self) -> SeasonDTO | None:
        season = await self.seasons.current()
        return self._to_dto(season) if season is not None else None

    async def ensure_current_season(self, *, now: dt.datetime | None = None) -> SeasonDTO:
        now = now or dt.datetime.now(dt.UTC)
        current = await self.seasons.current(now=now)
        if current is not None:
            return self._to_dto(current)
        season = await self.seasons.create(
            name=f"Season {now:%Y-%m}",
            started_at=now,
            ends_at=self._add_months(now, self.SEASON_MONTHS),
            status="active",
        )
        return self._to_dto(season)

    async def end_season(self, season_id: int) -> None:
        await self.seasons.mark_ended(season_id)

    @staticmethod
    def _to_dto(season: ArenaSeason) -> SeasonDTO:
        return SeasonDTO(
            id=season.id,
            name=season.name,
            started_at=season.started_at,
            ends_at=season.ends_at,
            status=season.status,
            reward_pool_total=season.reward_pool_total,
        )

    @staticmethod
    def _add_months(value: dt.datetime, months: int) -> dt.datetime:
        month = value.month - 1 + months
        year = value.year + month // 12
        month = month % 12 + 1
        day = min(value.day, _days_in_month(year, month))
        return value.replace(year=year, month=month, day=day)


def _days_in_month(year: int, month: int) -> int:
    next_month = dt.date(year + 1, 1, 1) if month == 12 else dt.date(year, month + 1, 1)
    return (next_month - dt.date(year, month, 1)).days
