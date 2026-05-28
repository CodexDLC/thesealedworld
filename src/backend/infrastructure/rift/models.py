from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
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
    profile_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    generation_rules_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    text_vocabulary_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)


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
    approach_view_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    transition_text_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    generation_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)


class RiftInstanceState(Base, TimestampMixin, MetadataContextMixin, SchemaVersionMixin):
    __tablename__ = "rift_instance_states"

    rift_instance_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    setting_key: Mapped[str] = mapped_column(
        String(96),
        ForeignKey("rift_settings.setting_key", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    instance_version: Mapped[int] = mapped_column(default=1, nullable=False)
    generation_seed: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    scale_preset_key: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    assembly_preset_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    zones_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    graph_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    nodes_state_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    objectives_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    runtime_flags_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    state_meta_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)


class RiftRunState(Base, TimestampMixin, MetadataContextMixin, SchemaVersionMixin):
    __tablename__ = "rift_run_states"
    __table_args__ = (Index("ix_rift_run_instance_participant", "rift_instance_id", "participant_ref"),)

    rift_run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    rift_instance_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("rift_instance_states.rift_instance_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    participant_scope: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    participant_ref: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    current_zone_key: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    current_node_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    previous_node_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    heading: Mapped[str | None] = mapped_column(String(16), nullable=True)
    visited_node_ids: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    discovered_node_ids: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    active_encounter_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    entry_context_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    run_state_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)


class RiftPortalKey(Base, TimestampMixin, MetadataContextMixin, SchemaVersionMixin):
    __tablename__ = "rift_portal_keys"
    __table_args__ = (
        Index("ix_rift_portal_owner_status", "owner_type", "owner_id", "status"),
        Index("ix_rift_portal_source_ref", "source", "source_ref"),
    )

    portal_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    portal_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False, index=True)
    source_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    rift_key: Mapped[str | None] = mapped_column(String(96), nullable=True, index=True)
    entry_reason: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    entry_mode: Mapped[str] = mapped_column(String(64), default="direct", nullable=False)
    owner_type: Mapped[str] = mapped_column(String(32), default="character", nullable=False, index=True)
    owner_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    participant_scope: Mapped[str] = mapped_column(String(32), default="solo", nullable=False, index=True)
    rift_session_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    rift_instance_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    service_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source_location_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    exit_target_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    exit_location_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    entry_context_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    exit_policy_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    runtime_refs_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    state_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
