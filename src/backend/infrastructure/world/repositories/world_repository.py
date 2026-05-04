from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from src.backend.infrastructure.world.models import WorldGrid, WorldRegion, WorldZone

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class WorldRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def has_world_data(self) -> bool:
        stmt = select(func.count()).select_from(WorldGrid)
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0) > 0

    async def count_active_nodes(self) -> int:
        stmt = select(func.count()).select_from(WorldGrid).where(WorldGrid.is_active)
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def upsert_region(self, region: WorldRegion) -> None:
        stmt = pg_insert(WorldRegion).values(id=region.id, climate_tags=region.climate_tags)
        await self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={"climate_tags": stmt.excluded.climate_tags},
            )
        )

    async def upsert_zone(self, zone: WorldZone) -> None:
        stmt = pg_insert(WorldZone).values(
            id=zone.id,
            region_id=zone.region_id,
            biome_id=zone.biome_id,
            tier=zone.tier,
            flags=zone.flags,
        )
        await self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "region_id": stmt.excluded.region_id,
                    "biome_id": stmt.excluded.biome_id,
                    "tier": stmt.excluded.tier,
                    "flags": stmt.excluded.flags,
                },
            )
        )

    async def get_region(self, region_id: str) -> WorldRegion | None:
        result = await self.session.execute(select(WorldRegion).where(WorldRegion.id == region_id))
        return result.scalar_one_or_none()

    async def get_zone(self, zone_id: str) -> WorldZone | None:
        result = await self.session.execute(select(WorldZone).where(WorldZone.id == zone_id))
        return result.scalar_one_or_none()

    async def get_node(self, x: int, y: int) -> WorldGrid | None:
        result = await self.session.execute(select(WorldGrid).where(WorldGrid.x == x, WorldGrid.y == y))
        return result.scalar_one_or_none()

    async def get_nodes_in_rect(self, x: int, y: int, width: int, height: int) -> list[WorldGrid]:
        stmt = select(WorldGrid).where(
            WorldGrid.x >= x,
            WorldGrid.x < x + width,
            WorldGrid.y >= y,
            WorldGrid.y < y + height,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_nodes(self) -> list[WorldGrid]:
        stmt = select(WorldGrid).options(joinedload(WorldGrid.zone)).where(WorldGrid.is_active)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def bulk_upsert_nodes(self, nodes: list[dict[str, Any]]) -> None:
        if not nodes:
            return

        stmt = pg_insert(WorldGrid).values(nodes)
        await self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=["x", "y"],
                set_={
                    "zone_id": stmt.excluded.zone_id,
                    "terrain_type": stmt.excluded.terrain_type,
                    "services": stmt.excluded.services,
                    "content": stmt.excluded.content,
                    "is_active": stmt.excluded.is_active,
                    "flags": stmt.excluded.flags,
                },
            )
        )

    async def create_or_update_node(
        self,
        *,
        x: int,
        y: int,
        zone_id: str,
        terrain_type: str,
        is_active: bool = False,
        flags: dict[str, Any] | None = None,
        content: dict[str, Any] | None = None,
        services: list[str] | None = None,
    ) -> None:
        await self.bulk_upsert_nodes(
            [
                {
                    "x": x,
                    "y": y,
                    "zone_id": zone_id,
                    "terrain_type": terrain_type,
                    "is_active": is_active,
                    "flags": flags or {},
                    "content": content,
                    "services": services or [],
                }
            ]
        )

    async def update_flags(self, x: int, y: int, new_flags: dict[str, Any], *, activate_node: bool = False) -> bool:
        node = await self.get_node(x, y)
        if node is None:
            return False

        flags = dict(node.flags or {})
        flags.update(new_flags)
        values: dict[str, Any] = {"flags": flags}
        if activate_node:
            values["is_active"] = True

        try:
            await self.session.execute(update(WorldGrid).where(WorldGrid.x == x, WorldGrid.y == y).values(**values))
        except SQLAlchemyError:
            return False
        return True

    async def update_content(self, x: int, y: int, content: dict[str, Any]) -> bool:
        try:
            await self.session.execute(
                update(WorldGrid).where(WorldGrid.x == x, WorldGrid.y == y).values(content=content)
            )
        except SQLAlchemyError:
            return False
        return True
