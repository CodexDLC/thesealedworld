from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.core.database import Base, MetadataContextMixin, SchemaVersionMixin


class WorldRegion(Base, MetadataContextMixin, SchemaVersionMixin):
    __tablename__ = "world_regions"

    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    biome_id: Mapped[str] = mapped_column(String(50), nullable=False, default="wasteland", index=True)
    region_archetype: Mapped[str] = mapped_column(String(80), nullable=False, default="wild_region", index=True)
    tier_min: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    tier_max: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    navigation_profile_id: Mapped[str] = mapped_column(String(80), nullable=False, default="open_frontier", index=True)
    biome_mix: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    population_profile: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    anchor_influence: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    is_locked_frontier: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    climate_tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    zones: Mapped[list[WorldZone]] = relationship(
        "WorldZone",
        back_populates="region",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class WorldZone(Base, MetadataContextMixin, SchemaVersionMixin):
    __tablename__ = "world_zones"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    region_id: Mapped[str] = mapped_column(
        ForeignKey("world_regions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    biome_id: Mapped[str] = mapped_column(String(50), nullable=False)
    tier: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    zone_archetype: Mapped[str] = mapped_column(String(80), nullable=False, default="wild_core", index=True)
    navigation_profile_id: Mapped[str] = mapped_column(String(80), nullable=False, default="open_frontier", index=True)
    landmark_profile: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    population_tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    visual_profile: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    flags: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    region: Mapped[WorldRegion] = relationship("WorldRegion", back_populates="zones")
    nodes: Mapped[list[WorldGrid]] = relationship(
        "WorldGrid",
        back_populates="zone",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class WorldGrid(Base, MetadataContextMixin, SchemaVersionMixin):
    __tablename__ = "world_grid"

    x: Mapped[int] = mapped_column(Integer, primary_key=True)
    y: Mapped[int] = mapped_column(Integer, primary_key=True)
    zone_id: Mapped[str] = mapped_column(
        ForeignKey("world_zones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    biome_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    node_type: Mapped[str] = mapped_column(String(50), default="generic", nullable=False, index=True)
    terrain_type: Mapped[str] = mapped_column(String(50), nullable=False)
    navigation_profile_id: Mapped[str] = mapped_column(String(80), nullable=False, default="open_frontier", index=True)
    buildable_kind: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    landmark_profile: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    movement_profile: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    background_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    background_pool_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    visual_overrides: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    services: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    content: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    flags: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    zone: Mapped[WorldZone] = relationship("WorldZone", back_populates="nodes")

    __table_args__ = (Index("idx_world_active_path", "x", "y", "is_active"),)

    def __repr__(self) -> str:
        return f"<WorldGrid ({self.x}, {self.y}) terrain={self.terrain_type}>"
