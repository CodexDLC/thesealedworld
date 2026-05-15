import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.core.database import Base, SchemaVersionMixin


class ChatSession(Base, SchemaVersionMixin):
    """DM session between two players — openable as a separate chat window."""

    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_a_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    participant_b_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    metadata_: Mapped[dict[str, object]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    last_message_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    messages: Mapped[list["ChatSessionMessage"]] = relationship(back_populates="session")

    __table_args__ = (
        Index("ix_chat_sessions_participants", "participant_a_id", "participant_b_id", unique=True),
        {"schema": "chat"},
    )


class ChatSessionMessage(Base, SchemaVersionMixin):
    """Individual DM message within a session."""

    __tablename__ = "chat_session_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat.chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    content: Mapped[str] = mapped_column(nullable=False)
    metadata_: Mapped[dict[str, object]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    archived_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")

    __table_args__ = (Index("ix_chat_session_messages_session", "session_id", "created_at"), {"schema": "chat"})
