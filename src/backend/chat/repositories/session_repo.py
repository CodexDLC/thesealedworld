import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.chat.models.message import ChatThread
from src.backend.chat.repositories.message_repo import ChatThreadRepository


class ChatSessionRepository:
    """DM compatibility facade over the thread/member chat model."""

    def __init__(self, session: AsyncSession) -> None:
        self._threads = ChatThreadRepository(session)

    async def get_or_create(self, a_id: uuid.UUID, b_id: uuid.UUID) -> ChatThread:
        low, high = sorted([a_id, b_id])
        scope_id = f"{low}:{high}"
        return await self._threads.get_or_create_thread(
            thread_type="dm",
            scope_id=scope_id,
            member_ids=[low, high],
        )

    async def get_sessions_for(self, character_id: uuid.UUID) -> list[ChatThread]:
        return await self._threads.get_threads_for_member(character_id, thread_type="dm")

    async def touch_last_message(self, session_id: uuid.UUID, ts: datetime) -> None:
        thread = await self._threads.get_thread_by_id(session_id)
        if thread is not None:
            thread.last_message_at = ts
