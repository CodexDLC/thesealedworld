from loguru import logger as log

from src.backend.features.game_catalog.combat.resources.effects.definitions.buffs import BUFF_EFFECTS_CATALOG
from src.backend.features.game_catalog.combat.resources.effects.definitions.controls import CONTROL_EFFECTS_CATALOG
from src.backend.features.game_catalog.combat.resources.effects.definitions.debuffs import DEBUFF_EFFECTS_CATALOG
from src.backend.features.game_catalog.combat.resources.effects.definitions.dots import DOT_EFFECTS_CATALOG
from src.backend.features.game_catalog.combat.resources.effects.definitions.hots import HOT_EFFECTS_CATALOG
from src.backend.features.game_catalog.combat.resources.effects.schemas import EffectCatalogEntryDTO

EFFECT_CATALOG_REGISTRY: dict[str, EffectCatalogEntryDTO] = {}
EFFECT_CATALOG_BY_KEY: dict[str, EffectCatalogEntryDTO] = {}
_INITIALIZED = False


def _initialize_library() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return

    log.info("EffectLibraryInitializing")

    all_catalogs = [
        DOT_EFFECTS_CATALOG,
        HOT_EFFECTS_CATALOG,
        BUFF_EFFECTS_CATALOG,
        DEBUFF_EFFECTS_CATALOG,
        CONTROL_EFFECTS_CATALOG,
    ]
    for catalog in all_catalogs:
        for effect_id, entry in catalog.items():
            if effect_id in EFFECT_CATALOG_REGISTRY:
                log.bind(effect_id=effect_id).warning("EffectLibraryDuplicateEffectId")
            EFFECT_CATALOG_REGISTRY[effect_id] = entry
            EFFECT_CATALOG_BY_KEY[entry.key] = entry

    log.bind(effect_count=len(EFFECT_CATALOG_REGISTRY)).info("EffectLibraryLoaded")
    _INITIALIZED = True


# ==========================================
# PUBLIC API — catalog (primary)
# ==========================================


def get_effect_catalog_entry(effect_id: str) -> EffectCatalogEntryDTO | None:
    return EFFECT_CATALOG_REGISTRY.get(effect_id)


def get_effect_catalog_entry_by_key(key: str) -> EffectCatalogEntryDTO | None:
    return EFFECT_CATALOG_BY_KEY.get(key)


def get_all_effect_catalog_entries() -> list[EffectCatalogEntryDTO]:
    return list(EFFECT_CATALOG_REGISTRY.values())


# Auto-init
_initialize_library()
