from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base, MetadataContextMixin, SchemaVersionMixin, TimestampMixin


class RiftSetting(Base, TimestampMixin, MetadataContextMixin, SchemaVersionMixin):
    __tablename__ = "rift_settings"

    setting_key: Mapped[str] = mapped_column(String(96), primary_key=True)
    setting_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    biome_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    generation_version: Mapped[int] = mapped_column(default=1, nullable=False)
    normalized_tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    mongo_setting_doc_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    mongo_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    mongo_stored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RiftNodePoolRecord(Base, TimestampMixin, MetadataContextMixin, SchemaVersionMixin):
    __tablename__ = "rift_node_pool_records"
    __table_args__ = (
        UniqueConstraint("setting_key", "pool_node_key", name="uq_rift_node_pool_setting_node_key"),
        Index("ix_rift_node_pool_setting_role", "setting_key", "node_role"),
    )

    pool_node_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    setting_key: Mapped[str] = mapped_column(
        String(96),
        ForeignKey("rift_settings.setting_key", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pool_node_key: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    node_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    node_role: Mapped[str] = mapped_column(String(64), default="ordinary", nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    role_fit: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    mongo_node_doc_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    mongo_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    mongo_stored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RiftMembership(Base, TimestampMixin, MetadataContextMixin, SchemaVersionMixin):
    __tablename__ = "rift_memberships"
    __table_args__ = (
        UniqueConstraint("rift_session_id", name="uq_rift_memberships_session"),
        Index("ix_rift_memberships_participant_status", "participant_ref", "status"),
        Index("ix_rift_memberships_instance_status", "rift_instance_id", "status"),
        Index("ix_rift_memberships_snapshot", "mongo_snapshot_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rift_instance_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    rift_session_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    participant_ref: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    setting_key: Mapped[str] = mapped_column(
        String(96),
        ForeignKey("rift_settings.setting_key", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    mongo_snapshot_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    snapshot_version: Mapped[int] = mapped_column(default=0, nullable=False)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    current_node_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    previous_node_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    heading: Mapped[str | None] = mapped_column(String(16), nullable=True)
    active_encounter_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
