import uuid
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.chat.models.session import ChatSession, ChatSessionMessage


class ChatSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, a_id: uuid.UUID, b_id: uuid.UUID) -> ChatSession:
        low, high = sorted([a_id, b_id])
        q = select(ChatSession).where(
            ChatSession.participant_a_id == low,
            ChatSession.participant_b_id == high,
        )
        result = await self._session.execute(q)
        existing = result.scalar_one_or_none()
        if existing:
            return existing
        dm = ChatSession(participant_a_id=low, participant_b_id=high)
        self._session.add(dm)
        await self._session.flush()
        return dm

    async def get_sessions_for(self, character_id: uuid.UUID) -> list[ChatSession]:
        q = (
            select(ChatSession)
            .where(
                or_(
                    ChatSession.participant_a_id == character_id,
                    ChatSession.participant_b_id == character_id,
                )
            )
            .order_by(ChatSession.last_message_at.desc())
        )
        result = await self._session.execute(q)
        return list(result.scalars().all())

    async def get_messages(
        self,
        session_id: uuid.UUID,
        *,
        limit: int = 50,
        before: datetime | None = None,
    ) -> list[ChatSessionMessage]:
        q = (
            select(ChatSessionMessage)
            .where(ChatSessionMessage.session_id == session_id)
            .order_by(ChatSessionMessage.created_at.desc())
            .limit(limit)
        )
        if before:
            q = q.where(ChatSessionMessage.created_at < before)
        result = await self._session.execute(q)
        return list(result.scalars().all())

    async def bulk_insert_messages(self, messages: list[ChatSessionMessage]) -> None:
        self._session.add_all(messages)

    async def touch_last_message(self, session_id: uuid.UUID, ts: datetime) -> None:
        q = select(ChatSession).where(ChatSession.id == session_id)
        result = await self._session.execute(q)
        dm = result.scalar_one_or_none()
        if dm:
            dm.last_message_at = ts
