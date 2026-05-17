from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, String
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
    family_id: Mapped[str] = mapped_column(String, nullable=False)
    tier: Mapped[int] = mapped_column(Integer, nullable=False)
    zone_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    biome_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    generation_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    context_hash: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    unique_hash: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    raw_tags: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    flavor_content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    name_ru: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    members: Mapped[list[Monster]] = relationship(
        "Monster",
        back_populates="clan",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (Index("ix_clan_context_lookup", "context_hash", "tier"),)


class Monster(Base, TimestampMixin, LifecycleStatusMixin, MetadataContextMixin, SchemaVersionMixin):
    __tablename__ = "generated_monsters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generated_clans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_key: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    member_tier: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    threat_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    name_ru: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    text_content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    scaled_attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    scaled_skills: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    items: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    vitals: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    ai_profile: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    combat_actor_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    generation_meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    clan: Mapped[GeneratedClanORM] = relationship("GeneratedClanORM", back_populates="members")

    @property
    def threat(self) -> int:
        return self.threat_rating

    @property
    def family_id(self) -> str | None:
        return self.clan.family_id if self.clan else None

    __table_args__ = (Index("ix_monster_role_threat", "role", "threat_rating"),)


GeneratedMonsterORM = Monster
