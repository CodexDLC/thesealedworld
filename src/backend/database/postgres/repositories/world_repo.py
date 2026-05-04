from typing import Any

from loguru import logger as log
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.db_contract.i_world_repo import IWorldRepo
from src.backend.database.postgres.models import WorldGrid, WorldRegion, WorldZone


class WorldRepoORM(IWorldRepo):
    """
    ORM-реализация репозитория Мира (WorldRepo).
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_region(self, region_data: WorldRegion) -> None:
        """
        Создает или обновляет регион.
        """
        try:
            await self.session.merge(region_data)
        except SQLAlchemyError as e:
            log.error(f"WorldRepo | region upsert failed id={region_data.id} error={e}")
            raise

    async def upsert_zone(self, zone_data: WorldZone) -> None:
        """
        Создает или обновляет зону.
        """
        try:
            await self.session.merge(zone_data)
        except SQLAlchemyError as e:
            log.error(f"WorldRepo | zone upsert failed id={zone_data.id} error={e}")
            raise

    async def get_node(self, x: int, y: int) -> WorldGrid | None:
        """
        Получает ноду по координатам.
        """
        stmt = select(WorldGrid).where(WorldGrid.x == x, WorldGrid.y == y)
        try:
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            log.exception(f"WorldRepo | get_node failed x={x} y={y} error={e}")
            raise

    async def get_nodes_in_rect(self, x: int, y: int, width: int, height: int) -> list[WorldGrid]:
        """
        Получает ноды в прямоугольной области.
        """
        stmt = select(WorldGrid).where(
            WorldGrid.x >= x, WorldGrid.x < x + width, WorldGrid.y >= y, WorldGrid.y < y + height
        )
        try:
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            log.error(f"WorldRepo | get_nodes_in_rect failed x={x} y={y} error={e}")
            return []

    async def create_or_update_node(
        self,
        x: int,
        y: int,
        zone_id: str,
        terrain_type: str,
        is_active: bool = False,
        flags: dict | None = None,
        content: dict | None = None,
        services: list[str] | None = None,
    ) -> None:
        """
        Создает или обновляет одну ноду (обертка над bulk_upsert).
        """
        # Обертка для совместимости, если где-то вызывается по одной штуке
        payload = [
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
        await self.bulk_upsert_nodes(payload)

    async def bulk_upsert_nodes(self, nodes_data: list[dict]) -> None:
        """
        Массовая вставка или обновление нод.
        Args:
            nodes_data: Список словарей, ключи должны совпадать с колонками WorldGrid
                        (x, y, zone_id, terrain_type, is_active, flags, content, services)
        """
        if not nodes_data:
            return

        # 1. Готовим стейтмент для INSERT (Postgres)
        stmt = pg_insert(WorldGrid).values(nodes_data)

        # 2. Готовим стейтмент для ON CONFLICT UPDATE
        # Мы обновляем все поля, кроме первичных ключей (x, y)
        do_update_stmt = stmt.on_conflict_do_update(
            index_elements=["x", "y"],
            set_={
                "zone_id": stmt.excluded.zone_id,
                "terrain_type": stmt.excluded.terrain_type,
                "is_active": stmt.excluded.is_active,
                "flags": stmt.excluded.flags,
                "content": stmt.excluded.content,
                "services": stmt.excluded.services,
            },
        )

        try:
            await self.session.execute(do_update_stmt)
            # Внимание: flush/commit здесь не делаем, управляет вызывающий код (Unit of Work)
        except SQLAlchemyError as e:
            log.error(f"WorldRepo | bulk_upsert failed items={len(nodes_data)} error={e}")
            raise

    async def update_flags(self, x: int, y: int, new_flags: dict[str, Any], activate_node: bool = False) -> bool:
        """
        Обновляет флаги ноды.
        """
        node = await self.get_node(x, y)
        if not node:
            return False
        current_flags = dict(node.flags) if node.flags else {}
        current_flags.update(new_flags)
        values_to_update: dict[str, Any] = {"flags": current_flags}
        if activate_node:
            values_to_update["is_active"] = True
        stmt = update(WorldGrid).where(WorldGrid.x == x, WorldGrid.y == y).values(**values_to_update)
        try:
            await self.session.execute(stmt)
            return True
        except SQLAlchemyError as e:
            log.error(f"WorldRepo | update_flags failed x={x} y={y} error={e}")
            return False

    async def update_content(self, x: int, y: int, new_content: dict[str, Any]) -> bool:
        """
        Обновляет поле content для указанной ноды.
        Внимание: Этот метод полностью заменяет содержимое поля `content`, а не объединяет его.
        """
        stmt = update(WorldGrid).where(WorldGrid.x == x, WorldGrid.y == y).values(content=new_content)
        try:
            await self.session.execute(stmt)
            return True
        except SQLAlchemyError as e:
            log.error(f"WorldRepo | update_content failed x={x} y={y} error={e}")
            return False

    async def get_region(self, region_id: str) -> WorldRegion | None:
        """Получает регион по ID."""
        stmt = select(WorldRegion).where(WorldRegion.id == region_id)
        try:
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            log.exception(f"WorldRepo | get_region failed id={region_id} error={e}")
            raise

    async def get_all_regions(self) -> list[WorldRegion]:
        """Получает все регионы."""
        stmt = select(WorldRegion).order_by(WorldRegion.id)
        try:
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            log.exception(f"WorldRepo | get_all_regions failed error={e}")
            raise

    async def get_zone(self, zone_id: str) -> WorldZone | None:
        """Получает зону по ID."""
        stmt = select(WorldZone).where(WorldZone.id == zone_id)
        try:
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            log.exception(f"WorldRepo | get_zone failed id={zone_id} error={e}")
            raise

    async def get_zones_by_region(self, region_id: str) -> list[WorldZone]:
        """Получает зоны региона."""
        stmt = select(WorldZone).where(WorldZone.region_id == region_id)
        try:
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            log.exception(f"WorldRepo | get_zones_by_region failed region={region_id} error={e}")
            raise

    async def get_nodes_by_zone(self, zone_id: str) -> list[WorldGrid]:
        """Получает ноды зоны."""
        stmt = select(WorldGrid).where(WorldGrid.zone_id == zone_id).order_by(WorldGrid.y, WorldGrid.x)
        try:
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            log.exception(f"WorldRepo | get_nodes_by_zone failed zone={zone_id} error={e}")
            raise

    async def get_active_nodes(self) -> list[WorldGrid]:
        """Получает активные ноды."""
        from sqlalchemy.orm import joinedload

        stmt = select(WorldGrid).options(joinedload(WorldGrid.zone)).where(WorldGrid.is_active)
        try:
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            log.exception(f"WorldRepo | get_active_nodes failed error={e}")
            raise
