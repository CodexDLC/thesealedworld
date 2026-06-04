from __future__ import annotations

import datetime as dt  # noqa: TC003 - SQLAlchemy resolves mapped annotations at runtime.

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base, MetadataContextMixin, SchemaVersionMixin


class CombatFinalization(Base, MetadataContextMixin, SchemaVersionMixin):
    __tablename__ = "combat_finalizations"
    __table_args__ = (
        Index("ix_combat_finalizations_finished_at", "finished_at"),
        Index("ix_combat_finalizations_participant_char_ids", "participant_char_ids", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    combat_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="finalized", nullable=False, index=True)
    source: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    battle_type: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    location_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    arena_session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    winner_team: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    participant_char_ids: Mapped[list[int]] = mapped_column(JSONB, default=list, nullable=False)
    player_win: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    turns: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    persisted_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    mongo_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    mongo_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
