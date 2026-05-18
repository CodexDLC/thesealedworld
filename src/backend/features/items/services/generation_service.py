from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.backend.features.items.dto.instance import (
    GeneratedItemDTO,
    ItemGenerationRequestDTO,
    ItemPlacementRefDTO,
    RuntimeItemProjectionDTO,
)
from src.backend.features.items.resources.item_grade import GRADE_BY_RARITY_TIER
from src.backend.features.items.runtime import ItemFactory
from src.backend.features.items.services.catalog_service import ItemCatalogService
from src.backend.features.items.services.text_service import ITEM_TEXT_PROMPT_VERSION, ItemTextService

if TYPE_CHECKING:
    from src.backend.features.generation_ai import GenerationAIService
    from src.backend.features.items.integrations import ItemPersistenceIntegration


@dataclass(slots=True)
class ItemGenerationResultDTO:
    item_ids: list[str]
    items: list[GeneratedItemDTO] | None = None
    text_status: str = "not_requested"
    text_requested_item_ids: list[str] | None = None

    @property
    def item(self) -> GeneratedItemDTO | None:
        return self.items[0] if self.items and len(self.items) == 1 else None

    def model_dump(self, mode: str = "json") -> dict[str, Any]:
        return {
            "item_ids": self.item_ids,
            "item": self.item.model_dump(mode=mode) if self.item is not None else None,
            "items": [item.model_dump(mode=mode) for item in self.items] if self.items is not None else None,
            "text_status": self.text_status,
            "text_requested_item_ids": list(self.text_requested_item_ids or []),
        }


class ItemGenerationService:
    def __init__(
        self,
        persistence: ItemPersistenceIntegration | None = None,
        catalog: ItemCatalogService | None = None,
        generation_ai: GenerationAIService | None = None,
    ) -> None:
        self.persistence = persistence
        self.catalog = catalog or ItemCatalogService.load_default()
        self.factory = ItemFactory(self.catalog)
        self.text_service = ItemTextService(self.catalog)
        self.generation_ai = generation_ai

    async def generate_mechanical(self, request: ItemGenerationRequestDTO) -> ItemGenerationResultDTO:
        if self.persistence is None:
            raise RuntimeError("Item persistence is required for mechanical item generation")
        placement_ref = self._resolve_placement_ref(request)
        item = self.factory.generate_player_item(request)
        text_status = "pending" if self._should_request_ai_text(request) else "not_requested"
        text_requested = False
        generated_template_id: str | None = None
        text_service = self.text_service
        text_payload = text_service._build_payload(item, request)
        text_template_hash_payload = text_service._build_template_hash_payload(item, request)
        text_visual_hash = text_service.build_text_visual_hash(text_template_hash_payload)
        template = await self.persistence.get_text_visual_template_by_hash(text_visual_hash)
        if template is None:
            template = await self.persistence.create_text_visual_template(
                item,
                text_visual_hash=text_visual_hash,
                text_payload=text_payload,
                prompt_version=ITEM_TEXT_PROMPT_VERSION,
                text_status=text_status,
            )
            text_requested = text_status == "pending"
        else:
            text_status = str(getattr(template, "text_status", text_status) or text_status)
            item = item.model_copy(
                update={
                    "name": str(getattr(template, "name", item.name) or item.name),
                    "description": str(getattr(template, "description", item.description) or item.description),
                }
            )
        generated_template_id = str(getattr(template, "id", "")) if template is not None else None
        item = item.model_copy(
            update={
                "metadata": {
                    **item.metadata,
                    "text_visual_hash": text_visual_hash,
                    "generated_template_id": generated_template_id,
                    "text_prompt_version": ITEM_TEXT_PROMPT_VERSION,
                    "text_template_hash_payload": text_template_hash_payload,
                }
            }
        )
        item_id = await self.persistence.create_mechanical_item(
            item,
            placement_ref,
            text_status=text_status,
            origin_ref=request.origin_ref,
            generated_template_id=generated_template_id,
        )
        item = item.model_copy(update={"instance_id": item_id})
        return ItemGenerationResultDTO(
            item_ids=[item_id],
            items=[item] if request.return_item else None,
            text_status=text_status,
            text_requested_item_ids=[item_id] if text_requested else [],
        )

    async def generate_runtime(self, request: ItemGenerationRequestDTO) -> ItemGenerationResultDTO:
        item = self.factory.generate_runtime_item(request)
        return ItemGenerationResultDTO(
            item_ids=[],
            items=[item] if request.return_item else None,
            text_status="not_requested",
        )

    async def generate(self, request: ItemGenerationRequestDTO) -> ItemGenerationResultDTO:
        if request.generation_mode == "runtime":
            return await self.generate_runtime(request)
        return await self.generate_mechanical(request)

    async def generate_many_mechanical(self, requests: list[ItemGenerationRequestDTO]) -> ItemGenerationResultDTO:
        item_ids: list[str] = []
        items: list[GeneratedItemDTO] = []
        text_statuses: set[str] = set()
        text_requested_item_ids: list[str] = []
        for request in requests:
            result = await self.generate_mechanical(request)
            item_ids.extend(result.item_ids)
            if result.items:
                items.extend(result.items)
            text_statuses.add(result.text_status)
            text_requested_item_ids.extend(result.text_requested_item_ids or [])
        text_status = text_statuses.pop() if len(text_statuses) == 1 else "mixed"
        return ItemGenerationResultDTO(
            item_ids=item_ids,
            items=items or None,
            text_status=text_status,
            text_requested_item_ids=text_requested_item_ids,
        )

    async def generate_many(self, requests: list[ItemGenerationRequestDTO]) -> ItemGenerationResultDTO:
        item_ids: list[str] = []
        items: list[GeneratedItemDTO] = []
        text_statuses: set[str] = set()
        text_requested_item_ids: list[str] = []
        for request in requests:
            result = await self.generate(request)
            item_ids.extend(result.item_ids)
            if result.items:
                items.extend(result.items)
            text_statuses.add(result.text_status)
            text_requested_item_ids.extend(result.text_requested_item_ids or [])
        text_status = text_statuses.pop() if len(text_statuses) == 1 else "mixed"
        return ItemGenerationResultDTO(
            item_ids=item_ids,
            items=items or None,
            text_status=text_status,
            text_requested_item_ids=text_requested_item_ids,
        )

    async def generate_runtime_projections(
        self, requests: list[ItemGenerationRequestDTO]
    ) -> list[RuntimeItemProjectionDTO]:
        projections: list[RuntimeItemProjectionDTO] = []
        for request in requests:
            runtime_request = request.model_copy(update={"generation_mode": "runtime", "return_item": True})
            item_id = str(runtime_request.runtime_metadata.get("runtime_item_id") or uuid.uuid4())
            projections.append(self.factory.generate_runtime_projection(runtime_request, item_id=item_id))
        return projections

    async def enrich_text(self, item_id: str, request: ItemGenerationRequestDTO) -> GeneratedItemDTO | None:
        if self.persistence is None:
            raise RuntimeError("Item persistence is required for item text generation")
        item = await self.persistence.get_generated_item(item_id)
        if item is None:
            return None
        if not self._should_request_ai_text(request):
            return item
        if self.generation_ai is not None:
            from src.backend.features.items.tasks_ai import build_item_text_task_spec

            await self.generation_ai.enqueue_many([build_item_text_task_spec(item_id=item_id, request=request)])
        return item

    def _resolve_placement_ref(self, request: ItemGenerationRequestDTO) -> ItemPlacementRefDTO:
        if request.placement_ref is not None:
            return request.placement_ref
        if request.char_id is not None:
            return ItemPlacementRefDTO(holder_type="character", holder_id=str(request.char_id))
        return ItemPlacementRefDTO(
            holder_type="system", holder_id=request.source or "generated", storage_type="storage"
        )

    def _should_request_ai_text(self, request: ItemGenerationRequestDTO) -> bool:
        if request.generation_mode == "runtime":
            return False
        item_grade = request.item_grade or GRADE_BY_RARITY_TIER.get(request.rarity_tier, "common")
        return request.request_ai_text and item_grade != "common"
