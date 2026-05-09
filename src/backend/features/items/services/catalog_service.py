from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from src.backend.features.items.dto.catalog import (
    BaseItemTemplateDTO,
    CatalogEntryDTO,
    MaterialTemplateDTO,
    RarityConfigDTO,
    RawResourceTemplateDTO,
)
from src.backend.features.items.resources.affixes.catalog import AFFIX_CATALOG, BUNDLE_CATALOG

if TYPE_CHECKING:
    from src.backend.features.items.resources.affixes.schemas import (
        AffixBundleDTO as NewAffixBundleDTO,
    )
    from src.backend.features.items.resources.affixes.schemas import (
        AffixCatalogEntryDTO,
    )


@dataclass(slots=True)
class ItemCatalogService:
    base_items: dict[str, BaseItemTemplateDTO] = field(default_factory=dict)
    materials: dict[str, MaterialTemplateDTO] = field(default_factory=dict)
    raw_resources: dict[str, RawResourceTemplateDTO] = field(default_factory=dict)
    rarities: dict[int, RarityConfigDTO] = field(default_factory=dict)
    entries: dict[str, CatalogEntryDTO] = field(default_factory=dict)

    @classmethod
    def load_default(cls) -> ItemCatalogService:
        from src.backend.features.items.resources.bases import BASES_DB
        from src.backend.features.items.resources.materials import CRAFTING_MATERIALS_DB
        from src.backend.features.items.resources.rarity_config import RARITY_CONFIG
        from src.backend.features.items.resources.raw_resources import RAW_RESOURCES_DB

        service = cls()
        service._load_base_items(BASES_DB)
        service._load_materials(CRAFTING_MATERIALS_DB)
        service._load_raw_resources(RAW_RESOURCES_DB)
        service.rarities = {int(tier): RarityConfigDTO.model_validate(config) for tier, config in RARITY_CONFIG.items()}
        return service

    def get_base_item(self, item_id: str) -> BaseItemTemplateDTO | None:
        return self.base_items.get(item_id)

    def get_material(self, material_id: str) -> MaterialTemplateDTO | None:
        return self.materials.get(material_id)

    def get_raw_resource(self, resource_id: str) -> RawResourceTemplateDTO | None:
        return self.raw_resources.get(resource_id)

    def get_affix_bundle(self, bundle_id: str) -> NewAffixBundleDTO | None:
        return BUNDLE_CATALOG.get(bundle_id)

    def get_rarity(self, tier: int) -> RarityConfigDTO:
        if not self.rarities:
            raise RuntimeError("Rarity catalog is not loaded")
        max_tier = max(self.rarities.keys())
        safe_tier = max(0, min(int(tier), max_tier))
        return self.rarities[safe_tier]

    def get_affix_entry(self, affix_id: str) -> AffixCatalogEntryDTO | None:
        return AFFIX_CATALOG.get(affix_id)

    def get_new_bundle(self, bundle_id: str) -> NewAffixBundleDTO | None:
        return self.get_affix_bundle(bundle_id)

    def get_material_for_tier(self, category: str, tier: int) -> MaterialTemplateDTO | None:
        matching = [
            material
            for entry in self.entries.values()
            if entry.meta_type == "material" and entry.category == category
            for material in [self.materials.get(entry.id)]
            if material is not None
        ]
        if not matching:
            return None
        index = max(0, min(int(tier), len(matching) - 1))
        return sorted(matching, key=lambda item: item.tier)[index]

    def by_id(self, item_id: str) -> CatalogEntryDTO | None:
        return self.entries.get(item_id)

    def all_public_text(self) -> dict[str, dict[str, object]]:
        result: dict[str, dict[str, object]] = {}
        for item_id, entry in self.entries.items():
            data = entry.data
            description = data.get("narrative_description") or data.get("description")
            result[item_id] = {
                "title": data.get("name_ru") or item_id,
                "description": description or f"DATA_MISSING: item_description:{item_id}",
                "type": entry.meta_type,
                "category": entry.category,
            }
        return result

    def _load_base_items(self, base_db: dict[str, dict[str, Any]]) -> None:
        for category, items in base_db.items():
            for item_id, raw in items.items():
                raw_dict = _as_dict(raw)
                if "id" not in raw_dict:
                    for nested_id, nested_raw in raw_dict.items():
                        self._add_base_item(nested_id, category, nested_raw)
                    continue
                self._add_base_item(item_id, category, raw_dict)

    def _add_base_item(self, item_id: str, category: str, raw: Any) -> None:
        item = BaseItemTemplateDTO.model_validate(_as_dict(raw))
        self._add_entry(item.id or item_id, "base", category, item)
        self.base_items[item.id] = item

    def _load_materials(self, materials_db: dict[str, dict[int, Any]]) -> None:
        for category, tier_map in materials_db.items():
            for tier_idx, raw in tier_map.items():
                raw_dict = _as_dict(raw)
                if not raw_dict.get("category"):
                    raw_dict = {**raw_dict, "category": category}
                raw_dict = {**raw_dict, "tier": int(tier_idx)}
                item = MaterialTemplateDTO.model_validate(raw_dict)
                self._add_entry(item.id, "material", category, item)
                self.materials[item.id] = item

    def _load_raw_resources(self, resources_db: dict[str, dict[Any, Any]]) -> None:
        for category, raw_map in resources_db.items():
            for _key, raw in raw_map.items():
                item = RawResourceTemplateDTO.model_validate(_as_dict(raw))
                self._add_entry(item.id, "resource", category, item)
                self.raw_resources[item.id] = item

    def _add_entry(self, item_id: str, meta_type: str, category: str, model: BaseModel) -> None:
        if item_id in self.entries:
            raise ValueError(f"Duplicate item catalog id: {item_id}")
        self.entries[item_id] = CatalogEntryDTO(
            id=item_id,
            meta_type=meta_type,
            category=category,
            data=model.model_dump(mode="json"),
        )


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, dict):
        return dict(value)
    raise TypeError(f"Unsupported item resource type: {type(value)!r}")
