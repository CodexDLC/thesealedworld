from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select, update

from src.frontend.features.feedback.models.feedback import Feedback

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


class FeedbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, feedback: Feedback) -> Feedback:
        self.session.add(feedback)
        await self.session.flush()
        await self.session.refresh(feedback)
        return feedback

    async def get_by_id(self, feedback_id: int) -> Feedback | None:
        result = await self.session.execute(select(Feedback).where(Feedback.id == feedback_id))
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: uuid.UUID) -> list[Feedback]:
        result = await self.session.execute(
            select(Feedback).where(Feedback.user_id == user_id).order_by(Feedback.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_type(self, feedback_type: str) -> list[Feedback]:
        result = await self.session.execute(
            select(Feedback).where(Feedback.type == feedback_type).order_by(Feedback.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_all(self) -> list[Feedback]:
        result = await self.session.execute(select(Feedback).order_by(Feedback.created_at.desc()))
        return list(result.scalars().all())

    async def update_status(self, feedback_id: int, status: str) -> None:
        stmt = update(Feedback).where(Feedback.id == feedback_id).values(status=status)
        await self.session.execute(stmt)

    async def commit(self) -> None:
        await self.session.commit()
