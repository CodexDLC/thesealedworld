from loguru import logger as log

from src.backend.features.game_catalog.combat.resources.effects.definitions.buffs import BUFF_EFFECTS_CATALOG
from src.backend.features.game_catalog.combat.resources.effects.definitions.controls import CONTROL_EFFECTS_CATALOG
from src.backend.features.game_catalog.combat.resources.effects.definitions.debuffs import DEBUFF_EFFECTS_CATALOG
from src.backend.features.game_catalog.combat.resources.effects.definitions.dots import DOT_EFFECTS_CATALOG
from src.backend.features.game_catalog.combat.resources.effects.definitions.hots import HOT_EFFECTS_CATALOG
from src.backend.features.game_catalog.combat.resources.effects.schemas import EffectCatalogEntryDTO, EffectDTO

EFFECT_CATALOG_REGISTRY: dict[str, EffectCatalogEntryDTO] = {}
EFFECT_CATALOG_BY_KEY: dict[str, EffectCatalogEntryDTO] = {}
_INITIALIZED = False


def _initialize_library() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return

    log.info("EffectLibrary | Initializing...")

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
                log.warning(f"EffectLibrary | Duplicate effect ID: '{effect_id}'. Overwriting.")
            EFFECT_CATALOG_REGISTRY[effect_id] = entry
            EFFECT_CATALOG_BY_KEY[entry.key] = entry

    log.info(f"EffectLibrary | Loaded {len(EFFECT_CATALOG_REGISTRY)} effects.")
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


# ==========================================
# COMPAT WRAPPERS — used by log_builder until that task migrates
# ==========================================


def get_effect_config(effect_id: str) -> EffectDTO | None:
    entry = EFFECT_CATALOG_REGISTRY.get(effect_id)
    return EffectDTO.from_catalog_entry(entry) if entry else None


def get_all_effects() -> list[EffectDTO]:
    return [EffectDTO.from_catalog_entry(e) for e in EFFECT_CATALOG_REGISTRY.values()]


# Auto-init
_initialize_library()
