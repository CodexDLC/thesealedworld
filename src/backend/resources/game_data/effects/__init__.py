from loguru import logger as log

from src.backend.resources.game_data.effects.definitions.buffs import BUFF_EFFECTS
from src.backend.resources.game_data.effects.definitions.controls import CONTROL_EFFECTS
from src.backend.resources.game_data.effects.definitions.debuffs import DEBUFF_EFFECTS
from src.backend.resources.game_data.effects.definitions.dots import DOT_EFFECTS
from src.backend.resources.game_data.effects.definitions.hots import HOT_EFFECTS
from src.backend.resources.game_data.effects.schemas import EffectDTO

# ==========================================
# ГЛОБАЛЬНЫЕ РЕЕСТРЫ (In-Memory DB)
# ==========================================

EFFECT_REGISTRY: dict[str, EffectDTO] = {}
_INITIALIZED = False


def _register_effects(effect_list: list[EffectDTO]) -> None:
    for effect in effect_list:
        if effect.effect_id in EFFECT_REGISTRY:
            log.warning(f"EffectLibrary | Duplicate effect ID: '{effect.effect_id}'. Overwriting.")
        EFFECT_REGISTRY[effect.effect_id] = effect


def _initialize_library() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return

    log.info("EffectLibrary | Initializing...")

    all_groups = [
        DOT_EFFECTS,
        HOT_EFFECTS,
        BUFF_EFFECTS,
        DEBUFF_EFFECTS,
        CONTROL_EFFECTS,
    ]
    count = 0

    for group in all_groups:
        _register_effects(group)
        count += len(group)

    log.info(f"EffectLibrary | Loaded {count} effects.")
    _INITIALIZED = True


# ==========================================
# PUBLIC API
# ==========================================


def get_effect_config(effect_id: str) -> EffectDTO | None:
    return EFFECT_REGISTRY.get(effect_id)


def get_all_effects() -> list[EffectDTO]:
    return list(EFFECT_REGISTRY.values())


# Auto-init
_initialize_library()
