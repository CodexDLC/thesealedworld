from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.items.dto.instance import GeneratedItemDTO

if TYPE_CHECKING:
    from src.backend.features.items.dto.instance import ItemOriginRefDTO, ItemPlacementRefDTO
    from src.backend.features.items.repositories import ItemInstanceRepository


class ItemPersistenceIntegration:
    """Items facade over item instance persistence."""

    def __init__(self, repo: ItemInstanceRepository) -> None:
        self.repo = repo

    async def create_mechanical_item(
        self,
        item: GeneratedItemDTO,
        placement_ref: ItemPlacementRefDTO,
        *,
        text_status: str,
        origin_ref: ItemOriginRefDTO | None = None,
        generated_template_id: str | None = None,
    ) -> str:
        instance = await self.repo.create_mechanical(
            item,
            placement_ref,
            text_status=text_status,
            origin_ref=origin_ref,
            generated_template_id=generated_template_id,
        )
        return str(instance.id)

    async def get_text_visual_template_by_hash(self, text_visual_hash: str) -> Any | None:
        return await self.repo.get_text_visual_template_by_hash(text_visual_hash)

    async def create_text_visual_template(
        self,
        item: GeneratedItemDTO,
        *,
        text_visual_hash: str,
        text_payload: dict[str, Any],
        prompt_version: str,
        text_status: str,
    ) -> Any:
        return await self.repo.create_text_visual_template(
            item,
            text_visual_hash=text_visual_hash,
            text_payload=text_payload,
            prompt_version=prompt_version,
            text_status=text_status,
        )

    async def get_generated_item(self, item_id: str) -> GeneratedItemDTO | None:
        instance = await self.repo.get(item_id)
        if instance is None:
            return None
        return self._dto_from_instance(instance)

    async def save_generated_text(self, item_id: str, item: GeneratedItemDTO) -> None:
        await self.repo.update_text(
            item_id,
            name=item.name,
            description=item.description,
            text_status="generated",
        )
        await self.repo.update_template_text_for_item(
            item_id,
            name=item.name,
            description=item.description,
            text_status="generated",
            metadata={
                "ai_text_status": item.metadata.get("ai_text_status"),
                "ai_prompt": item.metadata.get("ai_prompt"),
            },
        )

    async def mark_text_failed(self, item_id: str, reason: str | None = None) -> None:
        await self.repo.mark_text_failed(item_id, reason)

    async def transfer_deleted_character_items_to_system(self, character_id: int) -> int:
        return await self.repo.transfer_character_items_to_system(character_id)

    def _dto_from_instance(self, instance: Any) -> GeneratedItemDTO:
        return GeneratedItemDTO(
            instance_id=instance.id,
            template_id=str(instance.mechanics.get("template_id") or instance.base_id),
            item_type=instance.item_type,
            rarity=instance.rarity,
            rarity_tier=instance.rarity_tier,
            name=instance.name,
            description=instance.description,
            base_id=instance.base_id,
            material_id=instance.generation.get("material_id"),
            affix_bundle_ids=list(instance.generation.get("affix_bundle_ids") or []),
            power=float(instance.mechanics.get("power") or 0),
            durability_max=float(instance.mechanics.get("durability_max") or 0),
            damage_spread=float(instance.mechanics.get("damage_spread") or 0.1),
            slot=str(instance.mechanics.get("slot") or ""),
            valid_slots=list(instance.mechanics.get("valid_slots") or []),
            implicit_bonuses=dict(instance.mechanics.get("implicit_bonuses") or {}),
            bonuses=dict(instance.mechanics.get("bonuses") or {}),
            triggers=list(instance.mechanics.get("triggers") or []),
            narrative_tags=list(instance.generation.get("narrative_tags") or []),
            mechanics=dict(instance.mechanics or {}),
            metadata={
                **dict(instance.metadata_ or {}),
                "generated_template_id": getattr(instance, "generated_template_id", None),
            },
        )
