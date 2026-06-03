from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import select, update

from src.backend.features.items.models import (
    ItemGeneratedTemplate,
    ItemInstance,
    ItemOrigin,
    ItemPlacement,
    ItemTransaction,
)

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
        generated_template_id: str | None = None,
    ) -> ItemInstance:
        instance_id = item.instance_id or str(uuid.uuid4())
        mechanics = {
            **item.mechanics,
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
        }
        instance = ItemInstance(
            id=instance_id,
            generated_template_id=generated_template_id,
            base_id=item.base_id,
            item_type=item.item_type,
            rarity=item.rarity,
            rarity_tier=item.rarity_tier,
            lifecycle_status="ready" if text_status == "not_requested" else "mechanical_ready",
            text_status=text_status,
            name=item.name,
            description=item.description,
            mechanics=mechanics,
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

    async def get_text_visual_template_by_hash(self, text_visual_hash: str) -> ItemGeneratedTemplate | None:
        return await self.session.scalar(
            select(ItemGeneratedTemplate).where(ItemGeneratedTemplate.text_visual_hash == text_visual_hash)
        )

    async def create_text_visual_template(
        self,
        item: GeneratedItemDTO,
        *,
        text_visual_hash: str,
        text_payload: dict[str, Any],
        prompt_version: str,
        text_status: str,
    ) -> ItemGeneratedTemplate:
        template = ItemGeneratedTemplate(
            id=str(uuid.uuid4()),
            text_visual_hash=text_visual_hash,
            prompt_version=prompt_version,
            base_id=item.base_id,
            item_type=item.item_type,
            rarity=item.rarity,
            rarity_tier=item.rarity_tier,
            item_grade=str(item.metadata.get("item_grade") or ""),
            material_id=item.material_id,
            name=item.name,
            description=item.description,
            image_url=None,
            icon_key=str(item.metadata.get("icon_key") or "") or None,
            text_status=text_status,
            text_payload=text_payload,
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
        self.session.add(template)
        await self.session.flush()
        return template

    async def get(self, item_id: str) -> ItemInstance | None:
        return await self.session.scalar(select(ItemInstance).where(ItemInstance.id == item_id))

    async def get_equipped_for_characters(self, char_ids: list[int]) -> dict[int, list[dict[str, Any]]]:
        if not char_ids:
            return {}

        holder_ids = [str(char_id) for char_id in char_ids]
        result = await self.session.execute(
            select(ItemInstance, ItemPlacement)
            .join(ItemPlacement, ItemPlacement.item_id == ItemInstance.id)
            .where(
                ItemPlacement.holder_type == "character",
                ItemPlacement.holder_id.in_(holder_ids),
                ItemPlacement.storage_type == "equipped",
            )
        )

        equipped: dict[int, list[dict[str, Any]]] = {char_id: [] for char_id in char_ids}
        for instance, placement in result.all():
            try:
                char_id = int(placement.holder_id)
            except (TypeError, ValueError):
                continue
            equipped.setdefault(char_id, []).append(self._combat_item(instance, placement))
        return equipped

    async def transfer_character_items_to_system(
        self,
        character_id: int,
        *,
        holder_id: str | None = None,
        storage_type: str = "deleted_character_recovery",
        reason: str = "character_deleted",
    ) -> int:
        source_holder_id = str(character_id)
        target_holder_id = holder_id or f"deleted_character:{source_holder_id}"
        placements = (
            await self.session.scalars(
                select(ItemPlacement).where(
                    ItemPlacement.holder_type == "character",
                    ItemPlacement.holder_id == source_holder_id,
                )
            )
        ).all()

        for placement in placements:
            self.session.add(
                ItemTransaction(
                    item_id=placement.item_id,
                    from_holder_type=placement.holder_type,
                    from_holder_id=placement.holder_id,
                    from_storage_type=placement.storage_type,
                    to_holder_type="system",
                    to_holder_id=target_holder_id,
                    to_storage_type=storage_type,
                    reason=reason,
                )
            )
            placement.holder_type = "system"
            placement.holder_id = target_holder_id
            placement.storage_type = storage_type
            placement.slot = None
            placement.position_index = None
            placement.locked_by = None

        await self.session.flush()
        return len(placements)

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

    async def update_template_text_for_item(
        self,
        item_id: str,
        *,
        name: str,
        description: str,
        text_status: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        instance = await self.get(item_id)
        if instance is None or not instance.generated_template_id:
            return
        template = await self.session.get(ItemGeneratedTemplate, instance.generated_template_id)
        if template is None:
            return
        template.name = name
        template.description = description
        template.text_status = text_status
        if metadata:
            template.metadata_ = {**dict(template.metadata_ or {}), **metadata}
        await self.session.execute(
            update(ItemInstance)
            .where(ItemInstance.generated_template_id == instance.generated_template_id)
            .values(name=name, description=description, text_status=text_status)
        )
        await self.session.flush()

    async def mark_text_failed(self, item_id: str, reason: str | None = None) -> ItemInstance | None:
        instance = await self.get(item_id)
        if instance is None:
            return None
        instance.text_status = "failed"
        instance.metadata_ = {**instance.metadata_, "ai_text_status": "failed", "ai_text_reason": reason or "unknown"}
        await self.session.flush()
        return instance

    @staticmethod
    def _combat_item(instance: ItemInstance, placement: ItemPlacement) -> dict[str, Any]:
        mechanics = dict(instance.mechanics or {})

        # Lazy heal: compile bonuses from affixes for legacy items stored with bonuses={}
        if not mechanics.get("bonuses") and mechanics.get("affixes"):
            from src.backend.features.items.runtime.item_factory import ItemFactory

            mechanics["bonuses"] = ItemFactory._compile_affix_bonuses(mechanics["affixes"])

        metadata = {**dict(instance.metadata_ or {}), **dict(getattr(instance, "appearance", {}) or {})}
        slot = placement.slot or mechanics.get("slot")
        if slot:
            mechanics["slot"] = slot
        for key in ("related_skill", "damage_type", "defense_type", "armor_class"):
            if metadata.get(key) is not None:
                mechanics[key] = metadata[key]

        return {
            "item_id": str(instance.id),
            "base_id": instance.base_id,
            "item_type": instance.item_type,
            "slot": slot,
            "placement": placement.storage_type,
            "mechanics": mechanics,
            "tags": list((instance.generation or {}).get("narrative_tags") or []),
            "metadata": metadata,
            "name": instance.name,
            "description": instance.description,
            "rarity": instance.rarity,
            "rarity_tier": instance.rarity_tier,
        }
