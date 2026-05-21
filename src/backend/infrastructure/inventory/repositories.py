from loguru import logger as log
from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.infrastructure.inventory.models import InventoryItem, ResourceWallet


class InventoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.dto_adapter = TypeAdapter(dict)

    async def get_by_character_id(self, char_id: int) -> list[InventoryItem]:
        log.bind(char_id=char_id).debug("InventoryRepositoryGetByCharacterId")
        stmt = select(InventoryItem).where(InventoryItem.character_id == char_id)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_items_by_location_batch(self, char_ids: list[int], location: str) -> dict[int, list[dict]]:
        log.bind(char_id_count=len(char_ids), location=location).debug("InventoryRepositoryGetItemsByLocationBatch")
        if not char_ids:
            return {}
        stmt = select(InventoryItem).where(InventoryItem.character_id.in_(char_ids), InventoryItem.location == location)
        result = await self.session.scalars(stmt)
        items = list(result.all())

        by_id: dict[int, list[dict]] = {char_id: [] for char_id in char_ids}
        for item in items:
            item_dict = {
                "inventory_id": str(item.id),
                "character_id": item.character_id,
                "location": item.location,
                "item_type": item.item_type,
                "subtype": item.subtype,
                "rarity": item.rarity,
                "data": item.item_data,
                "quantity": item.quantity,
                "equipped_slot": item.equipped_slot,
                "quick_slot_position": item.quick_slot_position,
            }
            by_id[item.character_id].append(self.dto_adapter.validate_python(item_dict))
        return by_id


class WalletRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_character_id(self, char_id: int) -> ResourceWallet | None:
        log.bind(char_id=char_id).debug("WalletRepositoryGetByCharacterId")
        stmt = select(ResourceWallet).where(ResourceWallet.character_id == char_id)
        return await self.session.scalar(stmt)

    async def get_wallet(self, char_id: int) -> ResourceWallet | None:
        """Alias for get_by_character_id as expected by some services/tests."""
        return await self.get_by_character_id(char_id)
