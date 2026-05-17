from __future__ import annotations

import uuid  # noqa: TC003
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.core.database import (
    Base,
    LifecycleStatusMixin,
    MetadataContextMixin,
    RevisionMixin,
    SchemaVersionMixin,
    TimestampMixin,
)

if TYPE_CHECKING:
    from src.backend.features.character.models.progression import CharacterProgression
    from src.backend.features.character.models.skill import SkillProgress
    from src.backend.features.character.models.symbiote import CharacterSymbiote
    from src.backend.infrastructure.inventory.models import InventoryItem, ResourceWallet


class Character(Base, TimestampMixin, LifecycleStatusMixin, MetadataContextMixin, SchemaVersionMixin, RevisionMixin):
    __tablename__ = "characters"
    __table_args__ = (UniqueConstraint("name_key", name="uq_characters_name_key"),)

    character_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), default="New character", nullable=False)
    name_key: Mapped[str] = mapped_column(String(64), nullable=False)
    gender: Mapped[str] = mapped_column(String(20), default="other", nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    game_stage: Mapped[str] = mapped_column(String(50), default="creation", nullable=False)
    prev_game_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)

    location_id: Mapped[str] = mapped_column(String(50), default="52_52", nullable=False)
    prev_location_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    respawn_anchor_location_id: Mapped[str] = mapped_column(String(50), default="52_52", nullable=False)

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
    progression: Mapped[CharacterProgression] = relationship(
        "CharacterProgression",
        back_populates="character",
        cascade="all, delete-orphan",
        uselist=False,
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


class CharacterAttributes(Base, TimestampMixin, SchemaVersionMixin, RevisionMixin):
    __tablename__ = "character_attributes"

    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"),
        primary_key=True,
    )

    strength: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    agility: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    endurance: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    intellect: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    memory: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    mental: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    perception: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    projection: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    prediction: Mapped[int] = mapped_column(Integer, default=8, nullable=False)

    character: Mapped[Character] = relationship("Character", back_populates="attributes")
