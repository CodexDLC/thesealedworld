import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.core.database import Base, SchemaVersionMixin

if TYPE_CHECKING:
    from src.backend.chat.models.message import ChatThread


class ChatThreadMember(Base, SchemaVersionMixin):
    """Membership and read-state row for a chat thread."""

    __tablename__ = "chat_thread_members"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat.chat_threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    character_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="member", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    joined_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    last_read_message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    last_read_at: Mapped[datetime | None] = mapped_column(nullable=True)

    thread: Mapped["ChatThread"] = relationship(back_populates="members")

    __table_args__ = (
        UniqueConstraint("thread_id", "character_id", name="uq_chat_thread_members_thread_character"),
        Index("ix_chat_thread_members_character", "character_id", "status"),
        Index("ix_chat_thread_members_thread", "thread_id"),
        {"schema": "chat"},
    )
