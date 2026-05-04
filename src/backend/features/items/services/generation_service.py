from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.backend.features.items.dto.instance import GeneratedItemDTO, ItemGenerationRequestDTO, ItemPlacementRefDTO
from src.backend.features.items.runtime import ItemFactory
from src.backend.features.items.services.catalog_service import ItemCatalogService
from src.backend.features.items.services.text_service import ItemTextService

if TYPE_CHECKING:
    from src.backend.core.ai import AIService
    from src.backend.features.items.repositories import ItemInstanceRepository


@dataclass(slots=True)
class ItemGenerationResultDTO:
    item_ids: list[str]
    items: list[GeneratedItemDTO] | None = None
    text_status: str = "not_requested"

    @property
    def item(self) -> GeneratedItemDTO | None:
        return self.items[0] if self.items and len(self.items) == 1 else None

    def model_dump(self, mode: str = "json") -> dict[str, Any]:
        return {
            "item_ids": self.item_ids,
            "item": self.item.model_dump(mode=mode) if self.item is not None else None,
            "items": [item.model_dump(mode=mode) for item in self.items] if self.items is not None else None,
            "text_status": self.text_status,
        }


class ItemGenerationService:
    def __init__(
        self,
        repo: ItemInstanceRepository,
        ai: AIService | None = None,
        catalog: ItemCatalogService | None = None,
    ) -> None:
        self.repo = repo
        self.catalog = catalog or ItemCatalogService.load_default()
        self.factory = ItemFactory(self.catalog)
        self.text_service = ItemTextService(ai, self.catalog)

    async def generate_mechanical(self, request: ItemGenerationRequestDTO) -> ItemGenerationResultDTO:
        placement_ref = self._resolve_placement_ref(request)
        item = self.factory.generate(request)
        text_status = "pending" if request.request_ai_text else "not_requested"
        instance = await self.repo.create_mechanical(
            item,
            placement_ref,
            text_status=text_status,
            origin_ref=request.origin_ref,
        )
        item = item.model_copy(update={"instance_id": instance.id})
        return ItemGenerationResultDTO(
            item_ids=[instance.id],
            items=[item] if request.return_item else None,
            text_status=text_status,
        )

    async def generate_many_mechanical(self, requests: list[ItemGenerationRequestDTO]) -> ItemGenerationResultDTO:
        item_ids: list[str] = []
        items: list[GeneratedItemDTO] = []
        text_statuses: set[str] = set()
        for request in requests:
            result = await self.generate_mechanical(request)
            item_ids.extend(result.item_ids)
            if result.items:
                items.extend(result.items)
            text_statuses.add(result.text_status)
        text_status = text_statuses.pop() if len(text_statuses) == 1 else "mixed"
        return ItemGenerationResultDTO(item_ids=item_ids, items=items or None, text_status=text_status)

    async def enrich_text(self, item_id: str, request: ItemGenerationRequestDTO) -> GeneratedItemDTO | None:
        instance = await self.repo.get(item_id)
        if instance is None:
            return None
        item = self._dto_from_instance(instance)
        enriched = await self.text_service.enrich(item, request)
        if enriched.metadata.get("ai_text_status") == "generated":
            await self.repo.update_text(
                item_id,
                name=enriched.name,
                description=enriched.description,
                text_status="generated",
            )
            return enriched
        await self.repo.mark_text_failed(item_id, str(enriched.metadata.get("ai_text_reason") or "ai_failed"))
        return enriched

    def _resolve_placement_ref(self, request: ItemGenerationRequestDTO) -> ItemPlacementRefDTO:
        if request.placement_ref is not None:
            return request.placement_ref
        if request.char_id is not None:
            return ItemPlacementRefDTO(holder_type="character", holder_id=str(request.char_id))
        return ItemPlacementRefDTO(holder_type="system", holder_id=request.source or "generated", storage_type="storage")

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
            metadata=instance.metadata_,
        )
