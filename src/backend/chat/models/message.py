import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.core.database import Base, SchemaVersionMixin

if TYPE_CHECKING:
    from src.backend.chat.models.session import ChatThreadMember


class ChatThread(Base, SchemaVersionMixin):
    """Stable chat thread/index record. Message bodies live in Mongo buckets."""

    __tablename__ = "chat_threads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_type: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    metadata_: Mapped[dict[str, object]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    last_message_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    last_message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    members: Mapped[list["ChatThreadMember"]] = relationship(
        back_populates="thread",
        cascade="all, delete-orphan",
    )
    message_index: Mapped[list["ChatMessageIndex"]] = relationship(
        back_populates="thread",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("thread_type", "scope_id", name="uq_chat_threads_type_scope"),
        Index("ix_chat_threads_type_last_message", "thread_type", "last_message_at"),
        Index("ix_chat_threads_scope", "thread_type", "scope_id"),
        {"schema": "chat"},
    )


class ChatMessageIndex(Base, SchemaVersionMixin):
    """Postgres navigation row for a Mongo-backed chat message body."""

    __tablename__ = "chat_message_index"

    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat.chat_threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    mongo_collection: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mongo_bucket_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    bucket_seq: Mapped[int | None] = mapped_column(nullable=True)
    mongo_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    mongo_stored_at: Mapped[datetime | None] = mapped_column(nullable=True)

    thread: Mapped[ChatThread] = relationship(back_populates="message_index")

    __table_args__ = (
        Index("ix_chat_message_index_thread_created", "thread_id", "created_at"),
        Index("ix_chat_message_index_sender_created", "sender_id", "created_at"),
        Index("ix_chat_message_index_mongo_status", "mongo_status"),
        Index("ix_chat_message_index_bucket", "mongo_collection", "mongo_bucket_id"),
        {"schema": "chat"},
    )
