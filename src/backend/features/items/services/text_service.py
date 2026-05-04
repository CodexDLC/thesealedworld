from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, ValidationError

from src.backend.features.items.prompts.router import item_prompt_router
from src.backend.features.items.services.catalog_service import ItemCatalogService

if TYPE_CHECKING:
    from src.backend.core.ai import AIService
    from src.backend.features.items.dto.instance import GeneratedItemDTO, ItemGenerationRequestDTO

log = logging.getLogger(__name__)


class GeneratedItemTextDTO(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=500)


@dataclass(slots=True)
class ItemTextService:
    ai: AIService | None
    catalog: ItemCatalogService

    def __init__(self, ai: AIService | None, catalog: ItemCatalogService | None = None) -> None:
        self.ai = ai
        self.catalog = catalog or ItemCatalogService.load_default()
        if self.ai is not None:
            self.ai.include_router(item_prompt_router)

    async def enrich(self, item: GeneratedItemDTO, request: ItemGenerationRequestDTO) -> GeneratedItemDTO:
        if not request.request_ai_text:
            return item
        if self.ai is None:
            return self._mark_metadata(item, ai_text_status="skipped", ai_text_reason="ai_unavailable")

        payload = self._build_payload(item)
        try:
            raw_text = await self.ai.process("item_name_description", payload=payload)
            item_text = self._parse_response(raw_text)
        except Exception:
            log.exception("Failed to generate AI item text for template_id=%s", item.template_id)
            return self._mark_metadata(item, ai_text_status="failed")

        if item_text is None:
            return self._mark_metadata(item, ai_text_status="failed", ai_text_reason="empty_or_invalid_response")

        return item.model_copy(
            update={
                "name": item_text.name,
                "description": item_text.description,
                "metadata": {
                    **item.metadata,
                    "ai_text_status": "generated",
                    "ai_prompt": "item_name_description",
                },
            }
        )

    def _build_payload(self, item: GeneratedItemDTO) -> dict[str, Any]:
        base = self.catalog.get_base_item(item.base_id)
        material = self.catalog.get_material(item.material_id) if item.material_id else None
        rarity = self.catalog.get_rarity(item.rarity_tier)
        bundles = [
            bundle
            for bundle_id in item.affix_bundle_ids
            for bundle in [self.catalog.get_affix_bundle(bundle_id)]
            if bundle is not None
        ]
        effects_by_id = {
            effect_id: effect
            for bundle in bundles
            for effect_id in bundle.effects
            for effect in [self.catalog.get_affix_effect(effect_id)]
            if effect is not None
        }

        return {
            "base": {
                "id": item.base_id,
                "name_ru": base.name_ru if base else item.base_id,
                "narrative_description": base.narrative_description if base else item.description,
                "type": item.item_type,
                "slot": item.slot,
                "damage_type": base.damage_type if base else None,
                "defense_type": base.defense_type if base else None,
                "tags": base.narrative_tags if base else [],
            },
            "material": {
                "id": item.material_id,
                "name_ru": material.name_ru if material else None,
                "tags": material.narrative_tags if material else [],
            },
            "rarity": {
                "tier": item.rarity_tier,
                "key": item.rarity,
                "name_ru": rarity.name_ru,
            },
            "affixes": [
                {
                    "id": bundle.id,
                    "tags": bundle.narrative_tags,
                    "effects": [
                        {
                            "id": effect_id,
                            "target_field": effects_by_id[effect_id].target_field,
                            "tags": effects_by_id[effect_id].narrative_tags,
                        }
                        for effect_id in bundle.effects
                        if effect_id in effects_by_id
                    ],
                }
                for bundle in bundles
            ],
            "narrative_tags": item.narrative_tags,
        }

    def _parse_response(self, raw_text: Any) -> GeneratedItemTextDTO | None:
        if raw_text is None:
            return None
        raw_payload = json.loads(raw_text) if isinstance(raw_text, str) else raw_text
        try:
            return GeneratedItemTextDTO.model_validate(raw_payload)
        except ValidationError:
            log.warning("Invalid AI item text response: %r", raw_text)
            return None

    def _mark_metadata(self, item: GeneratedItemDTO, **metadata: object) -> GeneratedItemDTO:
        return item.model_copy(update={"metadata": {**item.metadata, **metadata}})
