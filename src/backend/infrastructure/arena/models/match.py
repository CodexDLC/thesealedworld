from __future__ import annotations

import datetime as dt  # noqa: TC003

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, SmallInteger, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base


class ArenaMatch(Base):
    __tablename__ = "arena_matches"
    __table_args__ = (
        Index("ix_arena_matches_completed_at", "completed_at"),
        Index("ix_arena_matches_team_a_members", "team_a_member_ids", postgresql_using="gin"),
        Index("ix_arena_matches_team_b_members", "team_b_member_ids", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    combat_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    arena_session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    mode_size: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    season_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("arena_seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    team_a_entity_type: Mapped[str] = mapped_column(String(16), nullable=False)
    team_a_entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    team_b_entity_type: Mapped[str] = mapped_column(String(16), nullable=False)
    team_b_entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    team_a_member_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger), nullable=False)
    team_b_member_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger), nullable=False)

    team_a_gs_locked: Mapped[int] = mapped_column(Integer, nullable=False)
    team_b_gs_locked: Mapped[int] = mapped_column(Integer, nullable=False)

    team_a_rating_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    team_a_rating_after: Mapped[int | None] = mapped_column(Integer, nullable=True)
    team_b_rating_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    team_b_rating_after: Mapped[int | None] = mapped_column(Integer, nullable=True)

    winner: Mapped[str] = mapped_column(String(8), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
