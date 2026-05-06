from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.chat.models.message import ChatMessage


class ChatMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_insert(self, messages: list[ChatMessage]) -> None:
        self._session.add_all(messages)

    async def get_history(
        self,
        channel_type: str,
        scope_id: str | None,
        *,
        limit: int = 50,
        before: datetime | None = None,
    ) -> list[ChatMessage]:
        q = (
            select(ChatMessage)
            .where(ChatMessage.channel_type == channel_type)
            .where(ChatMessage.scope_id == scope_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        if before:
            q = q.where(ChatMessage.created_at < before)
        result = await self._session.execute(q)
        return list(result.scalars().all())
