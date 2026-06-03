from src.backend.features.game_catalog.combat.resources.feints.definitions.basic_dodge import BASIC_DODGE_FEINTS_CATALOG
from src.backend.features.game_catalog.combat.resources.feints.definitions.basic_hit import BASIC_HIT_FEINTS_CATALOG
from src.backend.features.game_catalog.combat.resources.feints.definitions.basic_parry import BASIC_PARRY_FEINTS_CATALOG
from src.backend.features.game_catalog.combat.resources.feints.definitions.basic_pressure import (
    BASIC_PRESSURE_FEINTS_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.feints.definitions.basic_tempo import (
    BASIC_TEMPO_FEINTS_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.feints.definitions.tactical_dual_wield import (
    TACTICAL_DUAL_WIELD_FEINTS_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.feints.definitions.tactical_ranged import (
    TACTICAL_RANGED_FEINTS_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.feints.definitions.tactical_shield import (
    TACTICAL_SHIELD_FEINTS_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.feints.definitions.tactical_two_handed import (
    TACTICAL_TWO_HANDED_FEINTS_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.feints.definitions.weapon_archery import (
    WEAPON_ARCHERY_FEINTS_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.feints.definitions.weapon_dual_wield import (
    WEAPON_DUAL_WIELD_FEINTS_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.feints.definitions.weapon_fencing import (
    WEAPON_FENCING_FEINTS_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.feints.definitions.weapon_macing import (
    WEAPON_MACING_FEINTS_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.feints.definitions.weapon_polearms import (
    WEAPON_POLEARM_FEINTS_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.feints.definitions.weapon_shield import (
    WEAPON_SHIELD_FEINTS_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.feints.definitions.weapon_swords import (
    WEAPON_SWORD_FEINTS_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.feints.definitions.weapon_two_handed import (
    WEAPON_TWO_HANDED_FEINTS_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.feints.rendering import resolve_feint_render_context
from src.backend.features.game_catalog.combat.resources.feints.schemas import FeintCatalogEntryDTO

FEINT_CATALOG_REGISTRY: dict[str, FeintCatalogEntryDTO] = {
    **BASIC_DODGE_FEINTS_CATALOG,
    **BASIC_HIT_FEINTS_CATALOG,
    **BASIC_PARRY_FEINTS_CATALOG,
    **BASIC_PRESSURE_FEINTS_CATALOG,
    **BASIC_TEMPO_FEINTS_CATALOG,
    **WEAPON_ARCHERY_FEINTS_CATALOG,
    **WEAPON_DUAL_WIELD_FEINTS_CATALOG,
    **WEAPON_FENCING_FEINTS_CATALOG,
    **WEAPON_MACING_FEINTS_CATALOG,
    **WEAPON_POLEARM_FEINTS_CATALOG,
    **WEAPON_SHIELD_FEINTS_CATALOG,
    **WEAPON_SWORD_FEINTS_CATALOG,
    **WEAPON_TWO_HANDED_FEINTS_CATALOG,
    **TACTICAL_RANGED_FEINTS_CATALOG,
    **TACTICAL_SHIELD_FEINTS_CATALOG,
    **TACTICAL_DUAL_WIELD_FEINTS_CATALOG,
    **TACTICAL_TWO_HANDED_FEINTS_CATALOG,
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
