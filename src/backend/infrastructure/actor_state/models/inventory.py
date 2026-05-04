from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.core.database import Base

if TYPE_CHECKING:
    from src.backend.infrastructure.actor_state.models.character import Character


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)
    subtype: Mapped[str] = mapped_column(String(30), nullable=False)
    rarity: Mapped[str] = mapped_column(String(20), default="shared", nullable=False)
    location: Mapped[str] = mapped_column(String(20), default="inventory", nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    item_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    equipped_slot: Mapped[str | None] = mapped_column(String(50), nullable=True)
    quick_slot_position: Mapped[str | None] = mapped_column(String(50), nullable=True)

    character: Mapped[Character] = relationship("Character", back_populates="inventory")


class ResourceWallet(Base):
    __tablename__ = "resource_wallets"

    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"),
        primary_key=True,
    )
    currency: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict, nullable=False)
    resources: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict, nullable=False)
    components: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict, nullable=False)

    character: Mapped[Character] = relationship("Character", back_populates="wallet")
