from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.dialects.postgresql import insert

from src.backend.infrastructure.arena.models import ArenaBrawlXP

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ArenaBrawlRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def award_xp(self, *, char_id: int, season_id: int, amount: int) -> None:
        stmt = insert(ArenaBrawlXP).values(char_id=char_id, season_id=season_id, xp=amount, matches_played=1)
        stmt = stmt.on_conflict_do_update(
            index_elements=[ArenaBrawlXP.char_id, ArenaBrawlXP.season_id],
            set_={
                "xp": ArenaBrawlXP.xp + amount,
                "matches_played": ArenaBrawlXP.matches_played + 1,
            },
        )
        await self.session.execute(stmt)
