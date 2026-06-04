from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.core.database import (
    Base,
    LifecycleStatusMixin,
    MetadataContextMixin,
    SchemaVersionMixin,
    TimestampMixin,
)


class GeneratedClanORM(Base, TimestampMixin, LifecycleStatusMixin, MetadataContextMixin, SchemaVersionMixin):
    __tablename__ = "generated_clans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    identity_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    context_identity: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    context_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    selected_traits: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    encounter_texts: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    generation_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    resource_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    mongo_document_id: Mapped[str | None] = mapped_column(String(96), nullable=True)
    mongo_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    mongo_stored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    members: Mapped[list[Monster]] = relationship(
        "Monster",
        back_populates="clan",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_generated_clans_family_context", "family_id", "context_hash"),
        Index("ix_generated_clans_resource_version", "resource_version"),
        Index("ix_generated_clans_mongo_document_id", "mongo_document_id"),
    )


class HabitatClanPoolEntryORM(Base, TimestampMixin, SchemaVersionMixin):
    __tablename__ = "monster_habitat_clan_pool_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    scope_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    clan_identity_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    family_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    pool_tier: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    habitat: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (
        UniqueConstraint("scope_type", "scope_id", "clan_identity_hash", name="uq_habitat_clan_pool_scope_clan"),
        Index("ix_habitat_clan_pool_scope_enabled", "scope_type", "scope_id", "enabled"),
        Index("ix_habitat_clan_pool_scope_tier", "scope_type", "scope_id", "pool_tier"),
    )


class Monster(Base, TimestampMixin, LifecycleStatusMixin, MetadataContextMixin, SchemaVersionMixin):
    __tablename__ = "generated_clan_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generated_clans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    member_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    short_description: Mapped[str] = mapped_column(String, nullable=False)
    min_tier: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    max_tier: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    mongo_actor_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    mongo_document_id: Mapped[str | None] = mapped_column(String(96), nullable=True)
    mongo_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    mongo_stored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    clan: Mapped[GeneratedClanORM] = relationship("GeneratedClanORM", back_populates="members")

    __table_args__ = (
        UniqueConstraint("clan_id", "variant_id", "member_hash", name="uq_generated_member_identity"),
        Index("ix_generated_members_clan_tier", "clan_id", "min_tier", "max_tier"),
        Index("ix_generated_members_clan_role", "clan_id", "role"),
        Index("ix_generated_members_mongo_document_id", "mongo_document_id"),
    )


GeneratedMonsterORM = Monster
