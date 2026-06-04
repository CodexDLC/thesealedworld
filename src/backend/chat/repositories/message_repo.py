import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.chat.models.message import ChatMessageIndex, ChatThread
from src.backend.chat.models.session import ChatThreadMember


class ChatThreadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_thread(
        self,
        *,
        thread_type: str,
        scope_id: str | None,
        member_ids: list[uuid.UUID] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> ChatThread:
        existing = await self.get_thread(thread_type=thread_type, scope_id=scope_id)
        if existing is not None:
            if member_ids:
                await self.ensure_members(existing.id, member_ids)
            return existing
        thread = ChatThread(thread_type=thread_type, scope_id=scope_id, metadata_=metadata or {})
        self._session.add(thread)
        await self._session.flush()
        if member_ids:
            await self.ensure_members(thread.id, member_ids)
        return thread

    async def get_thread(self, *, thread_type: str, scope_id: str | None) -> ChatThread | None:
        result = await self._session.execute(
            select(ChatThread)
            .where(ChatThread.thread_type == thread_type)
            .where(ChatThread.scope_id == scope_id)
            .options(selectinload(ChatThread.members))
        )
        return result.scalar_one_or_none()

    async def get_thread_by_id(self, thread_id: uuid.UUID) -> ChatThread | None:
        result = await self._session.execute(
            select(ChatThread).where(ChatThread.id == thread_id).options(selectinload(ChatThread.members))
        )
        return result.scalar_one_or_none()

    async def ensure_members(self, thread_id: uuid.UUID, character_ids: list[uuid.UUID]) -> None:
        if not character_ids:
            return
        result = await self._session.execute(
            select(ChatThreadMember.character_id).where(ChatThreadMember.thread_id == thread_id)
        )
        existing = set(result.scalars().all())
        for character_id in dict.fromkeys(character_ids):
            if character_id in existing:
                continue
            self._session.add(ChatThreadMember(thread_id=thread_id, character_id=character_id))
        await self._session.flush()

    async def get_threads_for_member(
        self, character_id: uuid.UUID, *, thread_type: str | None = None
    ) -> list[ChatThread]:
        query = (
            select(ChatThread)
            .join(ChatThreadMember, ChatThreadMember.thread_id == ChatThread.id)
            .where(ChatThreadMember.character_id == character_id)
            .where(ChatThreadMember.status == "active")
            .options(selectinload(ChatThread.members))
            .order_by(ChatThread.last_message_at.desc())
        )
        if thread_type:
            query = query.where(ChatThread.thread_type == thread_type)
        result = await self._session.execute(query)
        return list(result.scalars().unique().all())

    async def add_message_index(
        self,
        *,
        message_id: uuid.UUID,
        thread_id: uuid.UUID,
        sender_id: uuid.UUID,
        created_at: datetime,
        mongo_collection: str | None,
        mongo_bucket_id: str | None,
        bucket_seq: int | None,
        mongo_status: str,
    ) -> ChatMessageIndex:
        row = ChatMessageIndex(
            message_id=message_id,
            thread_id=thread_id,
            sender_id=sender_id,
            created_at=created_at,
            mongo_collection=mongo_collection,
            mongo_bucket_id=mongo_bucket_id,
            bucket_seq=bucket_seq,
            mongo_status=mongo_status,
            mongo_stored_at=datetime.now(UTC) if mongo_status == "stored" else None,
        )
        row = await self._session.merge(row)
        thread = await self.get_thread_by_id(thread_id)
        if thread is not None:
            thread.last_message_at = created_at
            thread.last_message_id = message_id
        await self._session.flush()
        return row

    async def get_history_index(
        self,
        thread_id: uuid.UUID,
        *,
        limit: int = 50,
        before: datetime | None = None,
    ) -> list[ChatMessageIndex]:
        query = (
            select(ChatMessageIndex)
            .where(ChatMessageIndex.thread_id == thread_id)
            .order_by(ChatMessageIndex.created_at.desc())
            .limit(limit)
        )
        if before is not None:
            query = query.where(ChatMessageIndex.created_at < before)
        result = await self._session.execute(query)
        return list(result.scalars().all())
