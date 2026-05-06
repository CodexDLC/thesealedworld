from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.config.settings import settings
from src.backend.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from src.backend.features.character.models.character import Character


class CharacterSymbiote(Base, TimestampMixin):
    __tablename__ = "character_symbiotes"

    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"),
        primary_key=True,
    )
    symbiote_name: Mapped[str] = mapped_column(String(50), default=settings.default_symbiote_name, nullable=False)
    gift_id: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)
    gift_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gift_rank: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    elements_resonance: Mapped[dict[str, int]] = mapped_column(
        JSONB,
        default=lambda: {
            "fire": 0,
            "water": 0,
            "earth": 0,
            "air": 0,
            "dark": 0,
            "arcane": 0,
            "light": 0,
            "nature": 0,
        },
        nullable=False,
    )

    character: Mapped[Character] = relationship("Character", back_populates="symbiote")
