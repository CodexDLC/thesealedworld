from abc import ABC, abstractmethod
from typing import Any

from src.shared.schemas.item import InventoryItemDTO


class IInventoryRepo(ABC):
    """
    Интерфейс для работы с таблицей предметов (`InventoryItem`).
    """

    @abstractmethod
    async def create_item(
        self,
        character_id: int,
        item_type: str,
        subtype: str,
        rarity: str,
        item_data: dict[str, Any],
        location: str = "inventory",
        quantity: int = 1,
        equipped_slot: str | None = None,
    ) -> int:
        pass

    @abstractmethod
    async def get_system_item_for_reuse(
        self, item_type: str, rarity: str, subtype: str | None = None
    ) -> InventoryItemDTO | None:
        pass

    @abstractmethod
    async def transfer_item(self, inventory_id: int, new_owner_id: int, new_location: str = "inventory") -> bool:
        pass

    @abstractmethod
    async def get_all_items(self, character_id: int) -> list[InventoryItemDTO]:
        pass

    @abstractmethod
    async def get_items_by_location(self, character_id: int, location: str) -> list[InventoryItemDTO]:
        pass

    @abstractmethod
    async def get_items_by_location_batch(
        self, character_ids: list[int], location: str
    ) -> dict[int, list[InventoryItemDTO]]:
        """
        Возвращает предметы для списка персонажей в указанной локации.

        Args:
            character_ids: Список ID персонажей.
            location: Локация предметов (inventory, equipped).

        Returns:
            Словарь {character_id: [items]}.
        """
        pass

    @abstractmethod
    async def get_equipped_items(self, character_id: int) -> list[InventoryItemDTO]:
        """
        Возвращает все экипированные предметы персонажа.
        Это предметы, у которых location='equipped'.
        """
        pass

    @abstractmethod
    async def get_item_by_id(self, inventory_id: int) -> InventoryItemDTO | None:
        pass

    @abstractmethod
    async def move_item(self, inventory_id: int, new_location: str) -> bool:
        pass

    @abstractmethod
    async def delete_item(self, inventory_id: int) -> bool:
        pass

    @abstractmethod
    async def update_item_data(self, inventory_id: int, new_data: dict[str, Any]) -> bool:
        pass

    @abstractmethod
    async def update_fields(self, inventory_id: int, update_data: dict[str, Any]) -> bool:
        pass
