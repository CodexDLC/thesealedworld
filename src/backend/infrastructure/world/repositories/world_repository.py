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

    async def upsert_region(
        self,
        region_id: str | WorldRegion,
        *,
        climate_tags: list[str] | None = None,
        context: dict[str, Any] | None = None,
        biome_id: str | None = None,
        biome_mix: dict[str, Any] | None = None,
        region_archetype: str | None = None,
        tier_min: int | None = None,
        tier_max: int | None = None,
        navigation_profile_id: str | None = None,
        population_profile: dict[str, Any] | None = None,
        anchor_influence: dict[str, Any] | None = None,
        is_locked_frontier: bool = False,
    ) -> None:
        if isinstance(region_id, WorldRegion):
            climate_tags = region_id.climate_tags
            context = dict(region_id.context or {})
            biome_id = region_id.biome_id
            biome_mix = dict(region_id.biome_mix or {})
            region_archetype = region_id.region_archetype
            tier_min = region_id.tier_min
            tier_max = region_id.tier_max
            navigation_profile_id = region_id.navigation_profile_id
            population_profile = dict(region_id.population_profile or {})
            anchor_influence = dict(region_id.anchor_influence or {})
            is_locked_frontier = bool(region_id.is_locked_frontier)
            region_id = region_id.id
        stmt = pg_insert(WorldRegion).values(
            id=region_id,
            biome_id=biome_id or "wasteland",
            biome_mix=biome_mix or {},
            region_archetype=region_archetype or "wild_region",
            tier_min=tier_min or 0,
            tier_max=tier_max or 0,
            navigation_profile_id=navigation_profile_id or "open_frontier",
            population_profile=population_profile or {},
            anchor_influence=anchor_influence or {},
            is_locked_frontier=is_locked_frontier,
            climate_tags=climate_tags or [],
            context=context or {},
        )
        await self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "biome_id": stmt.excluded.biome_id,
                    "biome_mix": stmt.excluded.biome_mix,
                    "region_archetype": stmt.excluded.region_archetype,
                    "tier_min": stmt.excluded.tier_min,
                    "tier_max": stmt.excluded.tier_max,
                    "navigation_profile_id": stmt.excluded.navigation_profile_id,
                    "population_profile": stmt.excluded.population_profile,
                    "anchor_influence": stmt.excluded.anchor_influence,
                    "is_locked_frontier": stmt.excluded.is_locked_frontier,
                    "climate_tags": stmt.excluded.climate_tags,
                    "context": stmt.excluded.context,
                },
            )
        )

    async def upsert_zone(
        self,
        zone_id: str | WorldZone,
        *,
        region_id: str | None = None,
        biome_id: str | None = None,
        tier: int | None = None,
        flags: dict[str, Any] | None = None,
        zone_archetype: str | None = None,
        navigation_profile_id: str | None = None,
        landmark_profile: str | None = None,
        population_tags: list[str] | None = None,
    ) -> None:
        if isinstance(zone_id, WorldZone):
            zone = zone_id
            zone_id = zone.id
            region_id = zone.region_id
            biome_id = zone.biome_id
            tier = zone.tier
            flags = zone.flags
            zone_archetype = zone.zone_archetype
            navigation_profile_id = zone.navigation_profile_id
            landmark_profile = zone.landmark_profile
            population_tags = list(zone.population_tags or [])

        if region_id is None or biome_id is None or tier is None:
            raise ValueError("region_id, biome_id, and tier are required for upsert_zone")

        stmt = pg_insert(WorldZone).values(
            id=zone_id,
            region_id=region_id,
            biome_id=biome_id,
            tier=tier,
            zone_archetype=zone_archetype or "wild_core",
            navigation_profile_id=navigation_profile_id or "open_frontier",
            landmark_profile=landmark_profile,
            population_tags=population_tags or [],
            flags=flags or {},
        )
        await self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "region_id": stmt.excluded.region_id,
                    "biome_id": stmt.excluded.biome_id,
                    "tier": stmt.excluded.tier,
                    "zone_archetype": stmt.excluded.zone_archetype,
                    "navigation_profile_id": stmt.excluded.navigation_profile_id,
                    "landmark_profile": stmt.excluded.landmark_profile,
                    "population_tags": stmt.excluded.population_tags,
                    "flags": stmt.excluded.flags,
                },
            )
        )

    async def flush(self) -> None:
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()

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
                    "biome_id": stmt.excluded.biome_id,
                    "node_type": stmt.excluded.node_type,
                    "terrain_type": stmt.excluded.terrain_type,
                    "navigation_profile_id": stmt.excluded.navigation_profile_id,
                    "buildable_kind": stmt.excluded.buildable_kind,
                    "landmark_profile": stmt.excluded.landmark_profile,
                    "movement_profile": stmt.excluded.movement_profile,
                    "background_key": stmt.excluded.background_key,
                    "background_pool_key": stmt.excluded.background_pool_key,
                    "visual_overrides": stmt.excluded.visual_overrides,
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
                    "biome_id": None,
                    "node_type": "generic",
                    "terrain_type": terrain_type,
                    "navigation_profile_id": "open_frontier",
                    "buildable_kind": None,
                    "landmark_profile": None,
                    "movement_profile": {},
                    "background_key": None,
                    "background_pool_key": None,
                    "visual_overrides": {},
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
