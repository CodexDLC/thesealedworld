from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.backend.features.items.dto.instance import GeneratedItemDTO, ItemGenerationRequestDTO, ItemPlacementRefDTO
from src.backend.features.items.resources.item_grade import GRADE_BY_RARITY_TIER
from src.backend.features.items.runtime import ItemFactory
from src.backend.features.items.services.catalog_service import ItemCatalogService
from src.backend.features.items.services.text_service import ItemTextService

if TYPE_CHECKING:
    from src.backend.features.items.integrations import ItemPersistenceIntegration, ItemTextAIClient


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
        persistence: ItemPersistenceIntegration,
        text_ai_client: ItemTextAIClient | None = None,
        catalog: ItemCatalogService | None = None,
    ) -> None:
        self.persistence = persistence
        self.catalog = catalog or ItemCatalogService.load_default()
        self.factory = ItemFactory(self.catalog)
        self.text_service = ItemTextService(text_ai_client, self.catalog)

    async def generate_mechanical(self, request: ItemGenerationRequestDTO) -> ItemGenerationResultDTO:
        placement_ref = self._resolve_placement_ref(request)
        item = self.factory.generate(request)
        text_status = "pending" if self._should_request_ai_text(request) else "not_requested"
        item_id = await self.persistence.create_mechanical_item(
            item,
            placement_ref,
            text_status=text_status,
            origin_ref=request.origin_ref,
        )
        item = item.model_copy(update={"instance_id": item_id})
        return ItemGenerationResultDTO(
            item_ids=[item_id],
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
        item = await self.persistence.get_generated_item(item_id)
        if item is None:
            return None
        if not self._should_request_ai_text(request):
            return item
        enriched = await self.text_service.enrich(item, request)
        if enriched.metadata.get("ai_text_status") == "generated":
            await self.persistence.save_generated_text(item_id, enriched)
            return enriched
        await self.persistence.mark_text_failed(item_id, str(enriched.metadata.get("ai_text_reason") or "ai_failed"))
        return enriched

    def _resolve_placement_ref(self, request: ItemGenerationRequestDTO) -> ItemPlacementRefDTO:
        if request.placement_ref is not None:
            return request.placement_ref
        if request.char_id is not None:
            return ItemPlacementRefDTO(holder_type="character", holder_id=str(request.char_id))
        return ItemPlacementRefDTO(
            holder_type="system", holder_id=request.source or "generated", storage_type="storage"
        )

    def _should_request_ai_text(self, request: ItemGenerationRequestDTO) -> bool:
        item_grade = request.item_grade or GRADE_BY_RARITY_TIER.get(request.rarity_tier, "common")
        return request.request_ai_text and item_grade != "common"
