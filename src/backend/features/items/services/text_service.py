from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.backend.features.items.resources.item_grade import GRADE_BY_RARITY_TIER
from src.backend.features.items.services.catalog_service import ItemCatalogService

if TYPE_CHECKING:
    from src.backend.features.items.dto.instance import GeneratedItemDTO, ItemGenerationRequestDTO


@dataclass(slots=True)
class ItemTextService:
    catalog: ItemCatalogService

    def __init__(self, catalog: ItemCatalogService | None = None) -> None:
        self.catalog = catalog or ItemCatalogService.load_default()

    def _build_payload(self, item: GeneratedItemDTO, request: ItemGenerationRequestDTO) -> dict[str, Any]:
        base = self.catalog.get_base_item(item.base_id)
        material = self.catalog.get_material(item.material_id) if item.material_id else None
        item_grade = str(item.metadata.get("item_grade") or "") or GRADE_BY_RARITY_TIER.get(item.rarity_tier, "common")

        # Resolve affix narrative tags from new catalog
        affixes_payload: list[dict[str, Any]] = []
        mechanics = item.mechanics
        if isinstance(mechanics, dict):
            affixes = mechanics.get("affixes")
            if isinstance(affixes, list):
                for affix_record in affixes:
                    if not isinstance(affix_record, dict):
                        continue
                    affix_id = str(affix_record.get("affix_id", ""))
                    source = str(affix_record.get("source", ""))
                    entry = self.catalog.get_affix_entry(affix_id)
                    affix_tags = list(entry.descriptive.narrative_tags) if entry else []

                    if source.startswith("bundle:"):
                        bundle_id = source[len("bundle:") :]
                        bundle = self.catalog.get_new_bundle(bundle_id)
                        bundle_tags = list(bundle.tags) if bundle else []
                        # Group by bundle — accumulate affix_tags under same bundle entry
                        existing = next((a for a in affixes_payload if a.get("source") == source), None)
                        if existing is not None:
                            existing["affix_tags"].append(affix_tags)
                        else:
                            affixes_payload.append(
                                {
                                    "source": source,
                                    "bundle_tags": bundle_tags,
                                    "affix_tags": [affix_tags],
                                }
                            )
                    else:
                        affixes_payload.append(
                            {
                                "source": source,
                                "affix_tags": [affix_tags],
                            }
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
            "affixes": affixes_payload,
            "narrative_tags": item.narrative_tags,
        }

        if request.source_context:
            payload["source_context"] = request.source_context

        return payload
