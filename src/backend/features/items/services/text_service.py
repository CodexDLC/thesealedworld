from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.backend.features.items.services.catalog_service import ItemCatalogService

if TYPE_CHECKING:
    from src.backend.features.items.dto.instance import GeneratedItemDTO, ItemGenerationRequestDTO
    from src.backend.features.items.integrations import ItemTextAIClient

log = logging.getLogger(__name__)


@dataclass(slots=True)
class ItemTextService:
    ai_client: ItemTextAIClient | None
    catalog: ItemCatalogService

    def __init__(self, ai_client: ItemTextAIClient | None, catalog: ItemCatalogService | None = None) -> None:
        self.ai_client = ai_client
        self.catalog = catalog or ItemCatalogService.load_default()

    async def enrich(self, item: GeneratedItemDTO, request: ItemGenerationRequestDTO) -> GeneratedItemDTO:
        if not request.request_ai_text:
            return item
        if self.ai_client is None:
            return self._mark_metadata(item, ai_text_status="skipped", ai_text_reason="ai_unavailable")

        payload = self._build_payload(item)
        try:
            item_text = await self.ai_client.generate_item_text(payload)
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
                    "ai_prompt": self.ai_client.prompt_name,
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

    def _mark_metadata(self, item: GeneratedItemDTO, **metadata: object) -> GeneratedItemDTO:
        return item.model_copy(update={"metadata": {**item.metadata, **metadata}})
