from __future__ import annotations

from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base


class ItemInstance(Base):
    __tablename__ = "item_instances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    base_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    item_type: Mapped[str] = mapped_column(String(40), nullable=False)
    rarity: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    rarity_tier: Mapped[int] = mapped_column(nullable=False, index=True)
    lifecycle_status: Mapped[str] = mapped_column(String(40), default="mechanical_ready", nullable=False, index=True)
    text_status: Mapped[str] = mapped_column(String(40), default="not_requested", nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    mechanics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    appearance: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    generation: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[Any] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ItemPlacement(Base):
    __tablename__ = "item_placements"

    item_id: Mapped[str] = mapped_column(
        ForeignKey("item_instances.id", ondelete="CASCADE"),
        primary_key=True,
    )
    holder_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    holder_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    storage_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    slot: Mapped[str | None] = mapped_column(String(80), nullable=True)
    position_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[Any] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ResourceBalance(Base):
    __tablename__ = "resource_balances"
    __table_args__ = (
        UniqueConstraint("holder_type", "holder_id", "storage_type", "resource_key", name="uq_resource_balance_place"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    holder_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    holder_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    storage_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    resource_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[Any] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ItemOrigin(Base):
    __tablename__ = "item_origins"

    item_id: Mapped[str] = mapped_column(
        ForeignKey("item_instances.id", ondelete="CASCADE"),
        primary_key=True,
    )
    origin_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    origin_ref: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    seed: Mapped[str | None] = mapped_column(String(120), nullable=True)
    request_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    created_at: Mapped[Any] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ItemTransaction(Base):
    __tablename__ = "item_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    from_holder_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    from_holder_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    from_storage_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    to_holder_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_holder_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    to_storage_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    reason: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    created_at: Mapped[Any] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ResourceTransaction(Base):
    __tablename__ = "resource_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    from_holder_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    from_holder_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    from_storage_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    to_holder_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_holder_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    to_storage_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    reason: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    created_at: Mapped[Any] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
