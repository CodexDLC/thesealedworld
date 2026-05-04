# apps/shared/database/model_orm/character.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.database.postgres.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from .inventory import InventoryItem, ResourceWallet
    from .skill import CharacterSkillProgress
    from .symbiote import CharacterSymbiote
    from .user import User


class Character(Base, TimestampMixin):
    __tablename__ = "characters"

    character_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), default="Новый персонаж", nullable=False)
    gender: Mapped[str] = mapped_column(String(20), default="other", nullable=False)

    # FSM State и Навигация
    game_stage: Mapped[str] = mapped_column(
        String(50), default="creation", nullable=False, comment="Текущий FSM стейт (state)."
    )
    prev_game_stage: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Предыдущий FSM стейт (prev_state)."
    )

    location_id: Mapped[str] = mapped_column(String(50), default="52_52", nullable=False, comment="Текущая локация.")
    prev_location_id: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="Предыдущая локация.")

    # Snapshots (JSONB)
    vitals_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, comment="Снапшот HP/MP/Stamina."
    )
    active_sessions: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, comment="Активные сессии (combat_id, etc)."
    )

    user: Mapped[User] = relationship(back_populates="characters")

    # Renamed stats -> attributes
    attributes: Mapped[CharacterAttributes] = relationship(
        "CharacterAttributes", back_populates="character", cascade="all, delete-orphan"
    )

    skill_progress: Mapped[list[CharacterSkillProgress]] = relationship(
        "CharacterSkillProgress", back_populates="character", cascade="all, delete-orphan"
    )
    symbiote: Mapped[CharacterSymbiote] = relationship(
        "CharacterSymbiote", back_populates="character", cascade="all, delete-orphan", uselist=False
    )
    inventory: Mapped[list[InventoryItem]] = relationship(
        "InventoryItem", back_populates="character", cascade="all, delete-orphan"
    )
    wallet: Mapped[ResourceWallet] = relationship(
        "ResourceWallet", back_populates="character", cascade="all, delete-orphan", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Character(id={self.character_id}, name='{self.name}', user_id={self.user_id})>"


class CharacterAttributes(Base, TimestampMixin):
    """
    Таблица атрибутов персонажа (ранее CharacterStats).
    Хранит базовые параметры: Сила, Ловкость и т.д.
    """

    __tablename__ = "character_attributes"  # Renamed from character_stats

    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"), primary_key=True
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

    def __repr__(self) -> str:
        return f"<CharacterAttributes(character_id={self.character_id})>"


# Alias for backward compatibility (Optional)
CharacterStats = CharacterAttributes
