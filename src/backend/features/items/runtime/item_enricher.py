from __future__ import annotations

from src.backend.features.items.services.catalog_service import ItemCatalogService


class ItemEnricher:
    def __init__(self, catalog: ItemCatalogService | None = None) -> None:
        self.catalog = catalog or ItemCatalogService.load_default()

    def display_name(self, item_id: str) -> str:
        entry = self.catalog.by_id(item_id)
        if entry is None:
            return item_id.capitalize()
        return str(entry.data.get("name_ru") or item_id)
