from src.backend.features.game_catalog.combat.resources.feints.definitions.dirty import (
    DIRTY_FEINTS_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.feints.definitions.tactical import (
    TACTICAL_FEINTS_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.feints.definitions.tactical_techniques import (
    TACTICAL_TECHNIQUES_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.feints.definitions.weapon_moves import (
    WEAPON_FEINTS_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.feints.definitions.weapon_techniques import (
    WEAPON_TECHNIQUES_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.feints.rendering import resolve_feint_render_context
from src.backend.features.game_catalog.combat.resources.feints.schemas import FeintCatalogEntryDTO

FEINT_CATALOG_REGISTRY: dict[str, FeintCatalogEntryDTO] = {
    **WEAPON_TECHNIQUES_CATALOG,
    **TACTICAL_TECHNIQUES_CATALOG,
    **WEAPON_FEINTS_CATALOG,
    **TACTICAL_FEINTS_CATALOG,
    **DIRTY_FEINTS_CATALOG,
}
FEINT_CATALOG_BY_KEY: dict[str, FeintCatalogEntryDTO] = {entry.key: entry for entry in FEINT_CATALOG_REGISTRY.values()}


def get_feint_catalog_entry(feint_id: str) -> FeintCatalogEntryDTO | None:
    return FEINT_CATALOG_REGISTRY.get(feint_id)


def get_feint_catalog_entry_by_key(catalog_key: str) -> FeintCatalogEntryDTO | None:
    return FEINT_CATALOG_BY_KEY.get(catalog_key)


def get_all_feint_catalog_entries() -> list[FeintCatalogEntryDTO]:
    return list(FEINT_CATALOG_REGISTRY.values())


def get_feint_render_context(
    feint_id: str,
    *,
    skill_key: str | None,
    outcome: str,
    taxonomy: str = "humanoid",
    seed: str = "",
    bonus_damage: int | float = 0,
):
    entry = get_feint_catalog_entry(feint_id)
    if entry is None:
        return None
    return resolve_feint_render_context(
        feint_entry=entry,
        skill_key=skill_key,
        outcome=outcome,
        taxonomy=taxonomy,
        seed=seed,
        bonus_damage=bonus_damage,
    )
