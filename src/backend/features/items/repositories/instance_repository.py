from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select

from src.backend.features.items.models import ItemInstance, ItemOrigin, ItemPlacement

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.backend.features.items.dto.instance import GeneratedItemDTO, ItemOriginRefDTO, ItemPlacementRefDTO


class ItemInstanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_mechanical(
        self,
        item: GeneratedItemDTO,
        placement_ref: ItemPlacementRefDTO,
        *,
        text_status: str,
        origin_ref: ItemOriginRefDTO | None = None,
        correlation_id: str | None = None,
    ) -> ItemInstance:
        instance_id = item.instance_id or str(uuid.uuid4())
        instance = ItemInstance(
            id=instance_id,
            base_id=item.base_id,
            item_type=item.item_type,
            rarity=item.rarity,
            rarity_tier=item.rarity_tier,
            lifecycle_status="ready" if text_status == "not_requested" else "mechanical_ready",
            text_status=text_status,
            name=item.name,
            description=item.description,
            mechanics={
                "template_id": item.template_id,
                "slot": item.slot,
                "valid_slots": item.valid_slots,
                "power": item.power,
                "durability_current": item.durability_max,
                "durability_max": item.durability_max,
                "damage_spread": item.damage_spread,
                "implicit_bonuses": item.implicit_bonuses,
                "bonuses": item.bonuses,
                "triggers": item.triggers,
            },
            appearance={
                "width_cells": item.metadata.get("width_cells", 1),
                "height_cells": item.metadata.get("height_cells", 1),
                "volume_units": item.metadata.get("volume_units", 1),
                "icon_key": item.metadata.get("icon_key"),
            },
            generation={
                "material_id": item.material_id,
                "affix_bundle_ids": item.affix_bundle_ids,
                "narrative_tags": item.narrative_tags,
                "source": item.metadata.get("source"),
                "damage_type": item.metadata.get("damage_type"),
                "defense_type": item.metadata.get("defense_type"),
            },
            metadata_=item.metadata,
        )
        self.session.add(instance)
        self.session.add(
            ItemPlacement(
                item_id=instance_id,
                holder_type=placement_ref.holder_type,
                holder_id=placement_ref.holder_id,
                storage_type=placement_ref.storage_type,
                slot=placement_ref.slot,
                position_index=placement_ref.position_index,
            )
        )
        if origin_ref is not None:
            self.session.add(
                ItemOrigin(
                    item_id=instance_id,
                    origin_type=origin_ref.origin_type,
                    origin_ref=origin_ref.origin_ref,
                    seed=origin_ref.seed,
                    request_hash=origin_ref.request_hash,
                    correlation_id=correlation_id,
                )
            )
        await self.session.flush()
        return instance

    async def get(self, item_id: str) -> ItemInstance | None:
        return await self.session.scalar(select(ItemInstance).where(ItemInstance.id == item_id))

    async def update_text(self, item_id: str, *, name: str, description: str, text_status: str) -> ItemInstance | None:
        instance = await self.get(item_id)
        if instance is None:
            return None
        instance.name = name
        instance.description = description
        instance.text_status = text_status
        if text_status == "generated":
            instance.lifecycle_status = "ready"
        await self.session.flush()
        return instance

    async def mark_text_failed(self, item_id: str, reason: str | None = None) -> ItemInstance | None:
        instance = await self.get(item_id)
        if instance is None:
            return None
        instance.text_status = "failed"
        instance.metadata_ = {**instance.metadata_, "ai_text_status": "failed", "ai_text_reason": reason or "unknown"}
        await self.session.flush()
        return instance
