from __future__ import annotations

import datetime as dt  # noqa: TC003

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base, MetadataContextMixin, RevisionMixin, SchemaVersionMixin


class ArenaRating(Base, MetadataContextMixin, SchemaVersionMixin, RevisionMixin):
    """Long-table rating: one row per (entity, mode_size, season).

    entity_type: 'character' | 'team'.
    entity_id: characters.character_id or arena_teams.id (no FK because polymorphic).
    """

    __tablename__ = "arena_ratings"
    __table_args__ = (
        UniqueConstraint(
            "entity_type",
            "entity_id",
            "mode_size",
            "season_id",
            name="uq_arena_ratings_entity_mode_season",
        ),
        Index("ix_arena_ratings_leaderboard", "season_id", "mode_size", "rating"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(16), nullable=False)
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mode_size: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    season_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("arena_seasons.id", ondelete="CASCADE"),
        nullable=False,
    )

    rating: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    peak_rating: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    draws: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    league_tier: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    matches_played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    placement_left: Mapped[int] = mapped_column(SmallInteger, default=5, nullable=False)
    last_match_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
