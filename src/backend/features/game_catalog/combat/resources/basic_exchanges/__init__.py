from src.backend.features.game_catalog.combat.resources.basic_exchanges.definitions.natural_weapons import (
    NATURAL_WEAPON_BASIC_EXCHANGES_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.basic_exchanges.definitions.tactical_styles import (
    TACTICAL_STYLE_BASIC_EXCHANGES_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.basic_exchanges.definitions.weapon_mastery import (
    WEAPON_MASTERY_BASIC_EXCHANGES_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.basic_exchanges.schemas import BasicExchangeCatalogEntryDTO

BASIC_EXCHANGE_REGISTRY: dict[str, BasicExchangeCatalogEntryDTO] = {
    **WEAPON_MASTERY_BASIC_EXCHANGES_CATALOG,
    **NATURAL_WEAPON_BASIC_EXCHANGES_CATALOG,
    **TACTICAL_STYLE_BASIC_EXCHANGES_CATALOG,
}

BASIC_EXCHANGE_BY_KEY: dict[str, BasicExchangeCatalogEntryDTO] = {
    entry.key: entry for entry in BASIC_EXCHANGE_REGISTRY.values()
}


def get_basic_exchange_entry(exchange_id: str) -> BasicExchangeCatalogEntryDTO | None:
    return BASIC_EXCHANGE_REGISTRY.get(exchange_id)


def get_basic_exchange_entry_by_key(catalog_key: str) -> BasicExchangeCatalogEntryDTO | None:
    return BASIC_EXCHANGE_BY_KEY.get(catalog_key)


def get_all_basic_exchange_entries() -> list[BasicExchangeCatalogEntryDTO]:
    return list(BASIC_EXCHANGE_REGISTRY.values())
