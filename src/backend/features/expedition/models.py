from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base, MetadataContextMixin, RevisionMixin, SchemaVersionMixin, TimestampMixin


class CharacterExpedition(Base, TimestampMixin, MetadataContextMixin, SchemaVersionMixin, RevisionMixin):
    __tablename__ = "character_expeditions"

    run_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    start_location_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    current_location_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    respawn_anchor_location_id: Mapped[str] = mapped_column(String(50), default="52_52", nullable=False)
    pending_progress_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    corpse_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    corpse_location_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    corpse_public_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    corpse_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    death_combat_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    death_event_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    processed_events: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    __table_args__ = (Index("ix_character_expeditions_active_char", "character_id", "status"),)
