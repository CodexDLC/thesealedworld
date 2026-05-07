from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select, update

from src.backend.infrastructure.arena.models import ArenaTeam, ArenaTeamMembership

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ArenaTeamRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, team_id: int) -> ArenaTeam | None:
        result = await self.session.execute(select(ArenaTeam).where(ArenaTeam.id == team_id))
        return result.scalar_one_or_none()

    async def get_memberships(self, team_id: int) -> list[ArenaTeamMembership]:
        result = await self.session.execute(select(ArenaTeamMembership).where(ArenaTeamMembership.team_id == team_id))
        return list(result.scalars().all())

    async def get_active_team_for_char(self, *, char_id: int, size: int) -> ArenaTeam | None:
        result = await self.session.execute(
            select(ArenaTeam)
            .join(ArenaTeamMembership, ArenaTeamMembership.team_id == ArenaTeam.id)
            .where(
                ArenaTeamMembership.char_id == char_id,
                ArenaTeam.size == size,
                ArenaTeam.status == "active",
            )
        )
        return result.scalar_one_or_none()

    async def create(self, *, leader_id: int, name: str, size: int) -> ArenaTeam:
        team = ArenaTeam(leader_id=leader_id, name=name, size=size, status="active")
        self.session.add(team)
        await self.session.flush()
        self.session.add(ArenaTeamMembership(team_id=team.id, char_id=leader_id, role="leader"))
        await self.session.flush()
        return team

    async def add_member(self, *, team_id: int, char_id: int, role: str = "member") -> ArenaTeamMembership:
        membership = ArenaTeamMembership(team_id=team_id, char_id=char_id, role=role)
        self.session.add(membership)
        await self.session.flush()
        return membership

    async def remove_member(self, *, team_id: int, char_id: int) -> None:
        membership = await self.session.get(ArenaTeamMembership, {"team_id": team_id, "char_id": char_id})
        if membership is not None:
            await self.session.delete(membership)
            await self.session.flush()

    async def disband(self, team_id: int) -> None:
        await self.session.execute(update(ArenaTeam).where(ArenaTeam.id == team_id).values(status="disbanded"))
        await self.session.flush()
