from src.backend.features.game_catalog.combat.resources.feints.definitions.dirty import (
    DIRTY_FEINTS,
    DIRTY_FEINTS_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.feints.definitions.tactical import (
    TACTICAL_FEINTS,
    TACTICAL_FEINTS_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.feints.definitions.weapon_moves import (
    WEAPON_FEINTS,
    WEAPON_FEINTS_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.feints.schemas import FeintCatalogEntryDTO, FeintConfigDTO

FEINT_REGISTRY: dict[str, FeintConfigDTO] = {
    feint.feint_id: feint for feint in [*WEAPON_FEINTS, *TACTICAL_FEINTS, *DIRTY_FEINTS]
}
FEINT_CATALOG_REGISTRY: dict[str, FeintCatalogEntryDTO] = {
    **WEAPON_FEINTS_CATALOG,
    **TACTICAL_FEINTS_CATALOG,
    **DIRTY_FEINTS_CATALOG,
}
FEINT_CATALOG_BY_KEY: dict[str, FeintCatalogEntryDTO] = {
    entry.key: entry for entry in FEINT_CATALOG_REGISTRY.values()
}


def get_feint_config(feint_id: str) -> FeintConfigDTO | None:
    return FEINT_REGISTRY.get(feint_id)


def get_all_feints() -> list[FeintConfigDTO]:
    return list(FEINT_REGISTRY.values())


def get_feint_catalog_entry(feint_id: str) -> FeintCatalogEntryDTO | None:
    return FEINT_CATALOG_REGISTRY.get(feint_id)


def get_feint_catalog_entry_by_key(catalog_key: str) -> FeintCatalogEntryDTO | None:
    return FEINT_CATALOG_BY_KEY.get(catalog_key)


def get_all_feint_catalog_entries() -> list[FeintCatalogEntryDTO]:
    return list(FEINT_CATALOG_REGISTRY.values())
