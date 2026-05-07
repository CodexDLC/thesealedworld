from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import or_, select

from src.backend.infrastructure.arena.models import ArenaMatch

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ArenaMatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, match: ArenaMatch) -> ArenaMatch:
        self.session.add(match)
        await self.session.flush()
        return match

    async def get_by_combat_id(self, combat_id: str) -> ArenaMatch | None:
        result = await self.session.execute(select(ArenaMatch).where(ArenaMatch.combat_id == combat_id))
        return result.scalar_one_or_none()

    async def history(
        self,
        *,
        char_id: int | None = None,
        team_id: int | None = None,
        mode_size: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ArenaMatch]:
        stmt = select(ArenaMatch)
        if char_id is not None:
            stmt = stmt.where(
                or_(
                    ArenaMatch.team_a_member_ids.contains([char_id]),
                    ArenaMatch.team_b_member_ids.contains([char_id]),
                )
            )
        if team_id is not None:
            stmt = stmt.where(
                or_(
                    ArenaMatch.team_a_entity_id == team_id,
                    ArenaMatch.team_b_entity_id == team_id,
                )
            )
        if mode_size is not None:
            stmt = stmt.where(ArenaMatch.mode_size == mode_size)
        stmt = stmt.order_by(ArenaMatch.completed_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
