from src.backend.features.game_catalog.combat.resources.items.definitions import COMBAT_ITEM_ACTIONS_CATALOG
from src.backend.features.game_catalog.combat.resources.items.schemas import (
    CombatItemActionCatalogEntryDTO,
)

COMBAT_ITEM_ACTION_CATALOG_REGISTRY: dict[str, CombatItemActionCatalogEntryDTO] = dict(COMBAT_ITEM_ACTIONS_CATALOG)
COMBAT_ITEM_ACTION_CATALOG_BY_KEY: dict[str, CombatItemActionCatalogEntryDTO] = {
    entry.key: entry for entry in COMBAT_ITEM_ACTION_CATALOG_REGISTRY.values()
}


def get_combat_item_action_catalog_entry(item_action_id: str) -> CombatItemActionCatalogEntryDTO | None:
    return COMBAT_ITEM_ACTION_CATALOG_REGISTRY.get(item_action_id)


def get_combat_item_action_catalog_entry_by_key(catalog_key: str) -> CombatItemActionCatalogEntryDTO | None:
    return COMBAT_ITEM_ACTION_CATALOG_BY_KEY.get(catalog_key)


def get_all_combat_item_action_catalog_entries() -> list[CombatItemActionCatalogEntryDTO]:
    return list(COMBAT_ITEM_ACTION_CATALOG_REGISTRY.values())
