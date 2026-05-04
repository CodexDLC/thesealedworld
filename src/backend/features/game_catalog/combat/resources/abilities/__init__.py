from loguru import logger as log

from src.backend.features.game_catalog.combat.resources.abilities.definitions.debug import ABILITIES_DEFINITIONS
from src.backend.features.game_catalog.combat.resources.abilities.presets import PIPELINE_PRESETS
from src.backend.features.game_catalog.combat.resources.abilities.schemas import AbilityConfigDTO

# ==========================================
# ГЛОБАЛЬНЫЕ РЕЕСТРЫ (In-Memory DB)
# ==========================================

ABILITY_REGISTRY: dict[str, AbilityConfigDTO] = {}
_INITIALIZED = False


def _register_abilities(ability_list: list[AbilityConfigDTO]) -> None:
    for ability in ability_list:
        if ability.ability_id in ABILITY_REGISTRY:
            log.warning(f"AbilityLibrary | Duplicate ability ID: '{ability.ability_id}'. Overwriting.")
        ABILITY_REGISTRY[ability.ability_id] = ability


def _initialize_library() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return

    log.info("AbilityLibrary | Initializing...")

    # Собираем все группы определений (пока только одна)
    # Преобразуем values() словаря в список для регистрации
    all_groups = [list(ABILITIES_DEFINITIONS.values())]

    count = 0

    for group in all_groups:
        _register_abilities(group)
        count += len(group)

    log.info(f"AbilityLibrary | Loaded {count} abilities.")
    _INITIALIZED = True


# ==========================================
# PUBLIC API
# ==========================================


def get_ability_config(ability_id: str) -> AbilityConfigDTO | None:
    return ABILITY_REGISTRY.get(ability_id)


def get_all_abilities() -> list[AbilityConfigDTO]:
    return list(ABILITY_REGISTRY.values())


def get_pipeline_preset(preset_id: str) -> dict:
    return PIPELINE_PRESETS.get(preset_id, {})


# Auto-init
_initialize_library()
