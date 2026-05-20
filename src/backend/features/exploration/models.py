from __future__ import annotations

from datetime import datetime  # noqa: TC003

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base, MetadataContextMixin, RevisionMixin, SchemaVersionMixin, TimestampMixin


class CharacterLocationKnowledge(Base, TimestampMixin, MetadataContextMixin, SchemaVersionMixin, RevisionMixin):
    """Persistent per-character knowledge and XP budget state for one world location."""

    __tablename__ = "character_location_knowledge"
    __table_args__ = (
        UniqueConstraint("character_id", "loc_id", name="uq_character_location_knowledge_character_loc"),
        Index("ix_character_location_knowledge_character_updated", "character_id", "updated_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    loc_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    movement_xp_spent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    scouting_xp_spent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    hunting_xp_spent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    movement_xp_cap: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    scouting_xp_cap: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    hunting_xp_cap: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_visited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
