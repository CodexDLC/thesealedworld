from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.backend.features.character.models import Character
from src.backend.features.items.dto.instance import ItemGenerationRequestDTO, ItemOriginRefDTO, ItemPlacementRefDTO

if TYPE_CHECKING:
    from src.backend.features.generation_ai.services import GenerationAIService
    from src.backend.features.items.services.generation_service import ItemGenerationService


@dataclass(slots=True)
class AdminItemGrantResult:
    item_id: str
    generated_template_id: str | None
    text_visual_hash: str | None
    name: str
    description: str
    base_id: str
    rarity_tier: int
    text_status: str
    ai_text_task_requested: bool


class AdminItemGrantService:
    def __init__(
        self,
        *,
        session,
        item_generation: ItemGenerationService,
        generation_ai: GenerationAIService | None = None,
    ) -> None:
        self.session = session
        self.item_generation = item_generation
        self.generation_ai = generation_ai

    async def grant_to_character(
        self,
        *,
        char_id: int,
        base_id: str,
        rarity_tier: int = 1,
        material_id: str | None = None,
        item_grade: str = "",
        request_ai_text: bool = False,
        source: str = "admin:grant_character_item",
        source_context: dict[str, object] | None = None,
        seed_suffix: str | None = None,
    ) -> AdminItemGrantResult:
        character = await self.session.get(Character, char_id)
        if character is None:
            raise ValueError(f"Character not found: {char_id}")

        request = ItemGenerationRequestDTO(
            base_id=base_id,
            rarity_tier=rarity_tier,
            item_grade=item_grade,
            material_id=material_id,
            source=source,
            source_context=source_context or {},
            char_id=char_id,
            request_ai_text=request_ai_text,
            placement_ref=ItemPlacementRefDTO(
                holder_type="character",
                holder_id=str(char_id),
                storage_type="backpack",
                slot=None,
            ),
            origin_ref=ItemOriginRefDTO(
                origin_type="admin",
                origin_ref=source,
                seed=(
                    f"{source}:{char_id}:{base_id}:{rarity_tier}:"
                    f"{material_id or 'auto'}:{item_grade or 'auto'}:{seed_suffix or '0'}"
                ),
            ),
            return_item=True,
        )
        result = await self.item_generation.generate_mechanical(request)
        item = result.item
        if item is None:
            raise RuntimeError("Item generation did not return the generated item payload")

        ai_text_task_requested = False
        if request_ai_text and result.text_requested_item_ids and self.generation_ai is not None:
            for item_id in result.text_requested_item_ids:
                await self.item_generation.enrich_text(item_id, request)
            ai_text_task_requested = True

        return AdminItemGrantResult(
            item_id=result.item_ids[0],
            generated_template_id=_string_or_none(item.metadata.get("generated_template_id")),
            text_visual_hash=_string_or_none(item.metadata.get("text_visual_hash")),
            name=item.name,
            description=item.description,
            base_id=item.base_id,
            rarity_tier=item.rarity_tier,
            text_status=result.text_status,
            ai_text_task_requested=ai_text_task_requested,
        )


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None
