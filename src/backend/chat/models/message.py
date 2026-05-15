import uuid
from datetime import datetime

from sqlalchemy import Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base, SchemaVersionMixin


class ChatMessage(Base, SchemaVersionMixin):
    """Archived chat message — all channel types including DM."""

    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_type: Mapped[str] = mapped_column(String(16), nullable=False)
    scope_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sender_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sender_name: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict[str, object]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    archived_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_chat_messages_channel_scope", "channel_type", "scope_id", "created_at"),
        Index("ix_chat_messages_sender", "sender_id", "created_at"),
        {"schema": "chat"},
    )
