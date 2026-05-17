from __future__ import annotations

from datetime import datetime  # noqa: TC003

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base, MetadataContextMixin, RevisionMixin, SchemaVersionMixin, TimestampMixin


class CharacterTavernRoom(Base, TimestampMixin, MetadataContextMixin, SchemaVersionMixin, RevisionMixin):
    __tablename__ = "character_tavern_rooms"
    __table_args__ = (UniqueConstraint("character_id", "tavern_id", name="uq_character_tavern_rooms_character_tavern"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tavern_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    room_key: Mapped[str] = mapped_column(String(96), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
