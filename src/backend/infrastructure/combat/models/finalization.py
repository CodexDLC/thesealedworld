from __future__ import annotations

import datetime as dt  # noqa: TC003 - SQLAlchemy resolves mapped annotations at runtime.
from typing import Any

from sqlalchemy import BigInteger, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base


class CombatFinalization(Base):
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
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    persisted_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finalization: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    analytics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    report: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    reward_hooks: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
