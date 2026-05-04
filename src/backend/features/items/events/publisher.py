from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.core.bus import GameEventProducer
    from src.backend.features.items.dto.instance import GeneratedItemDTO, ItemGenerationRequestDTO


class ItemEvents:
    GENERATE_REQUESTED = "items.generate_requested"
    GENERATED = "items.generated"
    GENERATION_FAILED = "items.generation_failed"
    CATALOG_RELOADED = "items.catalog_reloaded"

    def __init__(self, events: GameEventProducer) -> None:
        self.events = events

    async def generate_requested(
        self,
        request: ItemGenerationRequestDTO,
        *,
        correlation_id: str | None = None,
    ) -> str:
        return await self.events.publish(
            self.GENERATE_REQUESTED,
            request.model_dump(mode="json"),
            correlation_id=correlation_id,
        )

    async def generated(
        self,
        item: GeneratedItemDTO,
        *,
        correlation_id: str | None = None,
    ) -> str:
        return await self.events.publish(
            self.GENERATED,
            item.model_dump(mode="json"),
            correlation_id=correlation_id,
        )

    async def generation_failed(
        self,
        request: ItemGenerationRequestDTO,
        error: str,
        *,
        correlation_id: str | None = None,
    ) -> str:
        return await self.events.publish(
            self.GENERATION_FAILED,
            {"request": request.model_dump(mode="json"), "error": error},
            correlation_id=correlation_id,
        )
