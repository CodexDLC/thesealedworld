from abc import ABC, abstractmethod
from typing import Any

from src.backend.database.postgres.models import WorldGrid, WorldRegion, WorldZone


class IWorldRepo(ABC):
    """
    Интерфейс для работы с картой мира (Регионы, Зоны, Сетка).
    Обеспечивает доступ к таблицам world_regions, world_zones и world_grid.
    """

    # --- РЕГИОНЫ (15x15) ---

    @abstractmethod
    async def upsert_region(self, region_data: WorldRegion) -> None:
        """
        Создает или обновляет запись о Регионе (D4).
        """
        pass

    @abstractmethod
    async def get_region(self, region_id: str) -> WorldRegion | None:
        """
        Получает регион по ID.
        """
        pass

    @abstractmethod
    async def get_all_regions(self) -> list[WorldRegion]:
        """
        Получает список всех регионов.
        """
        pass

    # --- ЗОНЫ (5x5) - NEW ---

    @abstractmethod
    async def upsert_zone(self, zone_data: WorldZone) -> None:
        """
        Создает или обновляет запись о Зоне (D4_1_1).
        Используется генератором для сохранения биома.
        """
        pass

    @abstractmethod
    async def get_zone(self, zone_id: str) -> WorldZone | None:
        """
        Получает зону по ID.
        """
        pass

    @abstractmethod
    async def get_zones_by_region(self, region_id: str) -> list[WorldZone]:
        """
        Получает все зоны внутри региона.
        """
        pass

    # --- КЛЕТКИ (Nodes 1x1) ---

    @abstractmethod
    async def get_node(self, x: int, y: int) -> WorldGrid | None:
        """
        Получает одну клетку по координатам.
        """
        pass

    @abstractmethod
    async def get_nodes_by_zone(self, zone_id: str) -> list[WorldGrid]:
        """
        Получает все клетки для указанной зоны.
        """
        pass

    @abstractmethod
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
        Полная запись клетки (UPSERT).
        Args:
            zone_id: Ссылка на таблицу WorldZone (D4_1_1).
            terrain_type: Ключ типа местности (thicket, edge, road).
            services: Список ключей сервисов.
        """
        pass

    @abstractmethod
    async def bulk_upsert_nodes(self, nodes_data: list[dict]) -> None:
        """
        Массовая вставка или обновление нод.
        """
        pass

    @abstractmethod
    async def update_flags(self, x: int, y: int, new_flags: dict[str, Any], activate_node: bool = False) -> bool:
        """
        Точечное обновление флагов.
        """
        pass

    @abstractmethod
    async def update_content(self, x: int, y: int, new_content: dict[str, Any]) -> bool:
        """
        Точечное обновление контента.
        """
        pass

    @abstractmethod
    async def get_active_nodes(self) -> list[WorldGrid]:
        """
        Возвращает список ВСЕХ активных клеток.
        """
        pass

    @abstractmethod
    async def get_nodes_in_rect(self, x: int, y: int, width: int, height: int) -> list[WorldGrid]:
        """
        Возвращает все клетки в прямоугольнике (для чанков).
        """
        pass
