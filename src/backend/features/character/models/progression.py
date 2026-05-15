from __future__ import annotations

from typing import Any

from sqlalchemy import Float, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.core.database import Base, ContextSourceMixin, RevisionMixin, SchemaVersionMixin, TimestampMixin


class CharacterProgression(Base, TimestampMixin, ContextSourceMixin, SchemaVersionMixin, RevisionMixin):
    __tablename__ = "character_progression"

    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"),
        primary_key=True,
    )
    free_xp: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    character: Mapped[Any] = relationship("Character", back_populates="progression")
