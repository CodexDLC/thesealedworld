from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.core.database import Base


class WorldRegion(Base):
    __tablename__ = "world_regions"

    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    climate_tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    zones: Mapped[list[WorldZone]] = relationship(
        "WorldZone",
        back_populates="region",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class WorldZone(Base):
    __tablename__ = "world_zones"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    region_id: Mapped[str] = mapped_column(
        ForeignKey("world_regions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    biome_id: Mapped[str] = mapped_column(String(50), nullable=False)
    tier: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    flags: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    region: Mapped[WorldRegion] = relationship("WorldRegion", back_populates="zones")
    nodes: Mapped[list[WorldGrid]] = relationship(
        "WorldGrid",
        back_populates="zone",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class WorldGrid(Base):
    __tablename__ = "world_grid"

    x: Mapped[int] = mapped_column(Integer, primary_key=True)
    y: Mapped[int] = mapped_column(Integer, primary_key=True)
    zone_id: Mapped[str] = mapped_column(
        ForeignKey("world_zones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    terrain_type: Mapped[str] = mapped_column(String(50), nullable=False)
    services: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    content: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    flags: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    zone: Mapped[WorldZone] = relationship("WorldZone", back_populates="nodes")

    __table_args__ = (Index("idx_world_active_path", "x", "y", "is_active"),)

    def __repr__(self) -> str:
        return f"<WorldGrid ({self.x}, {self.y}) terrain={self.terrain_type}>"
