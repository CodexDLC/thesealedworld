from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.backend.features.items.resources.item_grade import GRADE_BY_RARITY_TIER
from src.backend.features.items.services.catalog_service import ItemCatalogService

if TYPE_CHECKING:
    from src.backend.features.items.dto.instance import GeneratedItemDTO, ItemGenerationRequestDTO

ITEM_TEXT_PROMPT_VERSION = "item_name_description:mvp_text_visual_no_affixes:v1"


@dataclass(slots=True)
class ItemTextService:
    catalog: ItemCatalogService

    def __init__(self, catalog: ItemCatalogService | None = None) -> None:
        self.catalog = catalog or ItemCatalogService.load_default()

    def _build_payload(self, item: GeneratedItemDTO, request: ItemGenerationRequestDTO) -> dict[str, Any]:
        base = self.catalog.get_base_item(item.base_id)
        material = self.catalog.get_material(item.material_id) if item.material_id else None
        item_grade = str(item.metadata.get("item_grade") or "") or GRADE_BY_RARITY_TIER.get(
            item.rarity_tier, "no_grade"
        )

        narrative_tags = list(
            dict.fromkeys(
                [
                    *(base.narrative_tags if base else []),
                    *(material.narrative_tags if material else []),
                ]
            )
        )
        payload: dict[str, Any] = {
            "type": item.item_type,
            "slot": item.slot,
            "base_tags": base.narrative_tags if base else [],
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
                "name": material.name_ru if material else None,
                "tags": material.narrative_tags if material else [],
            },
            "grade": item_grade,
            "narrative_tags": narrative_tags,
        }

        if request.source_context:
            payload["source_context"] = request.source_context

        return payload

    def _build_template_hash_payload(self, item: GeneratedItemDTO, request: ItemGenerationRequestDTO) -> dict[str, Any]:
        source_context = request.source_context or {}
        owner_family = source_context.get("owner_family")
        clan_id = source_context.get("clan_id")
        if clan_id is None and isinstance(owner_family, dict):
            clan_id = owner_family.get("clan_id")

        return {
            "clan_id": str(clan_id) if clan_id is not None else None,
            "base_id": item.base_id,
            "item_tier": item.rarity_tier,
            "material_id": item.material_id,
        }

    def build_text_visual_hash(self, payload: dict[str, Any]) -> str:
        body = json.dumps(
            {"prompt_version": ITEM_TEXT_PROMPT_VERSION, "payload": payload},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(body.encode("utf-8")).hexdigest()
