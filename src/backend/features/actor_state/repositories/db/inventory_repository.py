from collections import defaultdict
from typing import Any

from loguru import logger as log
from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.features.actor_state.models import InventoryItem
from src.shared.schemas.item import InventoryItemDTO


class InventoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.dto_adapter: TypeAdapter[InventoryItemDTO] = TypeAdapter(InventoryItemDTO)

    async def get_items_by_location_batch(
        self,
        char_ids: list[int],
        location: str,
    ) -> dict[int, list[InventoryItemDTO]]:
        log.debug(
            f"InventoryRepository | action=get_items_by_location_batch count={len(char_ids)} location='{location}'"
        )
        if not char_ids:
            return {}

        stmt = select(InventoryItem).where(
            InventoryItem.character_id.in_(char_ids),
            InventoryItem.location == location,
        )
        try:
            result = await self.session.scalars(stmt)
            grouped_items: dict[int, list[InventoryItemDTO]] = defaultdict(list)
            for item in result.all():
                grouped_items[item.character_id].append(self._to_dto(item))
            return dict(grouped_items)
        except SQLAlchemyError as exc:
            log.exception(f"InventoryRepository | action=get_items_by_location_batch status=failed error={exc}")
            raise

    def _to_dto(self, orm_item: InventoryItem) -> InventoryItemDTO:
        dto_dict: dict[str, Any] = {
            "inventory_id": orm_item.id,
            "character_id": orm_item.character_id,
            "location": orm_item.location,
            "item_type": orm_item.item_type,
            "subtype": orm_item.subtype,
            "rarity": orm_item.rarity,
            "data": orm_item.item_data,
            "quantity": orm_item.quantity,
            "equipped_slot": orm_item.equipped_slot,
            "quick_slot_position": orm_item.quick_slot_position,
        }
        return self.dto_adapter.validate_python(dto_dict)


InventoryRepo = InventoryRepository
