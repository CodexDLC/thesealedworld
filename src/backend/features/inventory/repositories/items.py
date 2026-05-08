from __future__ import annotations

from typing import Any

from sqlalchemy import select

from src.backend.features.items.models import ItemInstance, ItemPlacement
from src.shared.schemas.inventory import InventoryRuntimeItemDTO


class InventoryItemRepository:
    def __init__(self, session: Any) -> None:
        self.session = session

    async def list_character_items(self, char_id: int) -> list[tuple[ItemInstance, ItemPlacement]]:
        result = await self.session.execute(
            select(ItemInstance, ItemPlacement)
            .join(ItemPlacement, ItemPlacement.item_id == ItemInstance.id)
            .where(ItemPlacement.holder_type == "character", ItemPlacement.holder_id == str(char_id))
            .order_by(ItemPlacement.position_index.nulls_last(), ItemInstance.name, ItemInstance.id)
        )
        return list(result.all())

    async def save_placements(self, char_id: int, items: dict[str, InventoryRuntimeItemDTO]) -> None:
        placements = {
            placement.item_id: placement
            for placement in await self.session.scalars(
                select(ItemPlacement).where(
                    ItemPlacement.holder_type == "character",
                    ItemPlacement.holder_id == str(char_id),
                )
            )
        }

        for item_id, item in items.items():
            placement = placements.get(item_id)
            if placement is None:
                continue
            placement.storage_type = item.placement
            placement.slot = item.slot
        await self.session.flush()

    async def flush(self) -> None:
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()


def runtime_item_from_instance(instance: ItemInstance, placement: ItemPlacement) -> InventoryRuntimeItemDTO:
    mechanics = dict(instance.mechanics or {})
    metadata = {**dict(instance.metadata_ or {}), **dict(getattr(instance, "appearance", {}) or {})}
    slot = placement.slot or mechanics.get("slot")
    if slot:
        mechanics["slot"] = slot

    valid_slots = mechanics.get("valid_slots")
    if not isinstance(valid_slots, list):
        valid_slots = [slot] if slot else []

    return InventoryRuntimeItemDTO(
        item_id=str(instance.id),
        base_id=instance.base_id,
        item_type=instance.item_type,
        slot=str(slot) if slot else None,
        valid_slots=[str(value) for value in valid_slots if value],
        placement=placement.storage_type,
        name=instance.name,
        description=instance.description,
        rarity=instance.rarity,
        rarity_tier=instance.rarity_tier,
        quantity=_quantity_from_item(metadata, mechanics),
        mechanics=mechanics,
        tags=list((instance.generation or {}).get("narrative_tags") or []),
        metadata=metadata,
    )


def _quantity_from_item(metadata: dict[str, Any], mechanics: dict[str, Any]) -> int:
    for raw in (
        metadata.get("quantity"),
        metadata.get("stack_count"),
        metadata.get("count"),
        mechanics.get("quantity"),
        mechanics.get("stack_count"),
        mechanics.get("charges"),
    ):
        if raw is not None:
            try:
                value = int(raw)
            except (TypeError, ValueError):
                continue
            if value > 0:
                return value
    return 1
