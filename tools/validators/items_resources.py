from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.items.services.catalog_service import ItemCatalogService

if TYPE_CHECKING:
    from pathlib import Path


def validate_items_resources(root: Path) -> list[str]:
    errors: list[str] = []
    try:
        catalog = ItemCatalogService.load_default()
    except Exception as exc:  # noqa: BLE001
        return [f"items resources failed to load: {exc.__class__.__name__}: {exc}"]

    material_categories = {
        entry.category for entry in catalog.entries.values() if entry.meta_type == "material"
    }
    resource_ids = set(catalog.raw_resources)
    material_ids = set(catalog.materials)

    for base in catalog.base_items.values():
        for category in base.allowed_materials:
            if category not in material_categories:
                errors.append(f"items:{base.id}: unknown material category: {category}")

    for bundle in catalog.affix_bundles.values():
        for affix_id in bundle.affix_ids:
            if affix_id not in catalog.affix_effects:
                errors.append(f"items:affix:{bundle.id}: unknown effect: {affix_id}")

    missing_tiers = set(range(8)) - set(catalog.rarities)
    if missing_tiers:
        errors.append(f"items:rarity_config: missing tiers: {sorted(missing_tiers)}")

    return errors
