from __future__ import annotations

import uuid  # noqa: TC003
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from src.backend.infrastructure.db.actor_state.models.inventory import InventoryItem, ResourceWallet
    from src.backend.infrastructure.db.actor_state.models.skill import SkillProgress
    from src.backend.infrastructure.db.actor_state.models.symbiote import CharacterSymbiote


class Character(Base, TimestampMixin):
    __tablename__ = "characters"

    character_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), default="New character", nullable=False)
    gender: Mapped[str] = mapped_column(String(20), default="other", nullable=False)

    game_stage: Mapped[str] = mapped_column(String(50), default="creation", nullable=False)
    prev_game_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)

    location_id: Mapped[str] = mapped_column(String(50), default="52_52", nullable=False)
    prev_location_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    vitals_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    active_sessions: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    attributes: Mapped[CharacterAttributes] = relationship(
        "CharacterAttributes",
        back_populates="character",
        cascade="all, delete-orphan",
    )
    skill_progress: Mapped[list[SkillProgress]] = relationship(
        "SkillProgress",
        back_populates="character",
        cascade="all, delete-orphan",
    )
    symbiote: Mapped[CharacterSymbiote] = relationship(
        "CharacterSymbiote",
        back_populates="character",
        cascade="all, delete-orphan",
        uselist=False,
    )
    inventory: Mapped[list[InventoryItem]] = relationship(
        "InventoryItem",
        back_populates="character",
        cascade="all, delete-orphan",
    )
    wallet: Mapped[ResourceWallet] = relationship(
        "ResourceWallet",
        back_populates="character",
        cascade="all, delete-orphan",
        uselist=False,
    )


class CharacterAttributes(Base, TimestampMixin):
    __tablename__ = "character_attributes"

    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"),
        primary_key=True,
    )

    strength: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    agility: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    endurance: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    intelligence: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    wisdom: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    men: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    perception: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    charisma: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    luck: Mapped[int] = mapped_column(Integer, default=8, nullable=False)

    character: Mapped[Character] = relationship("Character", back_populates="attributes")


CharacterStats = CharacterAttributes
