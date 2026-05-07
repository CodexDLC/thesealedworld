from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from src.backend.infrastructure.arena.models import ArenaSeasonReward

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ArenaSeasonRewardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_stub(
        self,
        *,
        season_id: int,
        entity_type: str,
        entity_id: int,
        payload: dict[str, Any] | None = None,
    ) -> ArenaSeasonReward:
        reward = ArenaSeasonReward(
            season_id=season_id,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {},
        )
        self.session.add(reward)
        await self.session.flush()
        return reward

    async def list_for_season(self, season_id: int) -> list[ArenaSeasonReward]:
        result = await self.session.execute(select(ArenaSeasonReward).where(ArenaSeasonReward.season_id == season_id))
        return list(result.scalars().all())
