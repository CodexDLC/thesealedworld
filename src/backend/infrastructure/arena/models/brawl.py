from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base, MetadataContextMixin, RevisionMixin, SchemaVersionMixin


class ArenaBrawlXP(Base, MetadataContextMixin, SchemaVersionMixin, RevisionMixin):
    __tablename__ = "arena_brawl_xp"

    char_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"),
        primary_key=True,
    )
    season_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("arena_seasons.id", ondelete="CASCADE"),
        primary_key=True,
    )
    xp: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    matches_played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
