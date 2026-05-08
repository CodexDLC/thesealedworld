from loguru import logger as log

from src.backend.features.game_catalog.combat.resources.abilities.definitions.debug import (
    ABILITIES_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.abilities.presets import PIPELINE_PRESETS
from src.backend.features.game_catalog.combat.resources.abilities.schemas import (
    AbilityCatalogEntryDTO,
    AbilityTechnicalDTO,
)

# ==========================================
# ГЛОБАЛЬНЫЕ РЕЕСТРЫ (In-Memory DB)
# ==========================================

ABILITY_REGISTRY: dict[str, AbilityTechnicalDTO] = {}
ABILITY_CATALOG_REGISTRY: dict[str, AbilityCatalogEntryDTO] = {}
ABILITY_CATALOG_BY_KEY: dict[str, AbilityCatalogEntryDTO] = {}
_INITIALIZED = False


def _register_abilities(ability_entries: list[AbilityCatalogEntryDTO]) -> None:
    for entry in ability_entries:
        ability = entry.technical
        if ability.ability_id in ABILITY_REGISTRY:
            log.warning(f"AbilityLibrary | Duplicate ability ID: '{ability.ability_id}'. Overwriting.")
        ABILITY_REGISTRY[ability.ability_id] = ability
        ABILITY_CATALOG_REGISTRY[ability.ability_id] = entry
        ABILITY_CATALOG_BY_KEY[entry.key] = entry


def _initialize_library() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return

    log.info("AbilityLibrary | Initializing...")

    # Собираем все группы определений (пока только одна)
    # Преобразуем values() словаря в список для регистрации
    all_groups = [list(ABILITIES_CATALOG.values())]

    count = 0

    for group in all_groups:
        _register_abilities(group)
        count += len(group)

    log.info(f"AbilityLibrary | Loaded {count} abilities.")
    _INITIALIZED = True


# ==========================================
# PUBLIC API
# ==========================================


def get_ability_config(ability_id: str) -> AbilityTechnicalDTO | None:
    return ABILITY_REGISTRY.get(ability_id)


def get_all_abilities() -> list[AbilityTechnicalDTO]:
    return list(ABILITY_REGISTRY.values())


def get_ability_catalog_entry(ability_id: str) -> AbilityCatalogEntryDTO | None:
    return ABILITY_CATALOG_REGISTRY.get(ability_id)


def get_ability_catalog_entry_by_key(catalog_key: str) -> AbilityCatalogEntryDTO | None:
    return ABILITY_CATALOG_BY_KEY.get(catalog_key)


def get_all_ability_catalog_entries() -> list[AbilityCatalogEntryDTO]:
    return list(ABILITY_CATALOG_REGISTRY.values())


def get_pipeline_preset(preset_id: str) -> dict:
    return PIPELINE_PRESETS.get(preset_id, {})


# Auto-init
_initialize_library()
