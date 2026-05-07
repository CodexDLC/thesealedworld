from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base


class ArenaLeague(Base):
    __tablename__ = "arena_leagues"
    __table_args__ = (UniqueConstraint("season_id", "tier", name="uq_arena_leagues_season_tier"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tier: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    min_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    max_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    season_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("arena_seasons.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
