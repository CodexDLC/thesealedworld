# app/shared/database/model_orm/world.py

from __future__ import annotations

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.database.postgres.models.base import Base, TimestampMixin


# ----------------------------------------------------------------------
# УРОВЕНЬ 1: РЕГИОН (15x15)
# ----------------------------------------------------------------------
class WorldRegion(Base):
    __tablename__ = "world_regions"

    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    climate_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    zones: Mapped[list[WorldZone]] = relationship(back_populates="region")


# ----------------------------------------------------------------------
# УРОВЕНЬ 2: ЗОНА (5x5)
# ----------------------------------------------------------------------
class WorldZone(Base):
    __tablename__ = "world_zones"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)

    region_id: Mapped[str] = mapped_column(
        ForeignKey("world_regions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    biome_id: Mapped[str] = mapped_column(String(50), nullable=False)

    tier: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 🔥 ДОБАВЛЯЕМ ЭТО ПОЛЕ (Fix ошибки TypeError)
    # Здесь будет лежать {"is_safe_zone": True} для Хаба.
    flags: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    region: Mapped[WorldRegion] = relationship(back_populates="zones")
    nodes: Mapped[list[WorldGrid]] = relationship(back_populates="zone")


# ----------------------------------------------------------------------
# УРОВЕНЬ 3: НОДА / КЛЕТКА (1x1)
# ----------------------------------------------------------------------
class WorldGrid(Base, TimestampMixin):
    __tablename__ = "world_grid"

    x: Mapped[int] = mapped_column(Integer, primary_key=True)
    y: Mapped[int] = mapped_column(Integer, primary_key=True)

    zone_id: Mapped[str] = mapped_column(ForeignKey("world_zones.id", ondelete="CASCADE"), nullable=False, index=True)

    terrain_type: Mapped[str] = mapped_column(String(50), nullable=False)
    services: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    content: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="{'title': '...', 'description': '...', 'tags': [...]}"
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Здесь лежат флаги клетки: {"has_road": True, "travel_cost": 0.5}
    flags: Mapped[dict] = mapped_column(JSON, default=dict)

    zone: Mapped[WorldZone] = relationship(back_populates="nodes")

    __table_args__ = (Index("idx_world_active_path", "x", "y", "is_active"),)

    def __repr__(self) -> str:
        return f"<Node ({self.x}, {self.y}) Type={self.terrain_type}>"
