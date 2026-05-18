from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.frontend.features.player_analytics.models.daily_activity import PlayerDailyActivity


class PlayerDailyActivityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_activity(self, player_id: str, activity_date: date, now: datetime) -> None:
        stmt = (
            pg_insert(PlayerDailyActivity)
            .values(
                player_id=uuid.UUID(player_id),
                date=activity_date,
                first_seen=now,
                last_seen=now,
            )
            .on_conflict_do_update(
                constraint="uq_player_daily_activity",
                set_={"last_seen": now},
            )
        )
        await self.session.execute(stmt)

    async def get_dau_history(self, days: int = 30) -> list[dict[str, object]]:
        cutoff = date.today() - timedelta(days=days)
        result = await self.session.execute(
            select(
                PlayerDailyActivity.date,
                func.count(func.distinct(PlayerDailyActivity.player_id)).label("dau"),
            )
            .where(PlayerDailyActivity.date >= cutoff)
            .group_by(PlayerDailyActivity.date)
            .order_by(PlayerDailyActivity.date.desc())
        )
        return [{"date": str(row.date), "dau": row.dau} for row in result.all()]

    async def get_today_dau(self) -> int:
        result = await self.session.execute(
            select(func.count(func.distinct(PlayerDailyActivity.player_id))).where(
                PlayerDailyActivity.date == date.today()
            )
        )
        return result.scalar_one() or 0
