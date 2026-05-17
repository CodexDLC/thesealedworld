from loguru import logger as log
from pydantic import ValidationError

from src.backend.features.monsters.dto.resources import MonsterFamilyDTO, MonsterVariantDTO

from .families.bandits import BANDITS_FAMILY
from .families.goblins import GOBLINS_FAMILY
from .families.rats import RATS_FAMILY
from .families.system.anchor_sovereigns import ANCHOR_SOVEREIGNS_FAMILY
from .families.wolves import WOLVES_FAMILY
from .monster_structs import MonsterFamily

STARTER_FAMILY_IDS: tuple[str, ...] = ("rat_swarm", "wolf_pack", "bandit_gang", "goblin_tribe")

ALL_FAMILIES_RAW: list[MonsterFamily] = [
    RATS_FAMILY,
    WOLVES_FAMILY,
    BANDITS_FAMILY,
    GOBLINS_FAMILY,
    ANCHOR_SOVEREIGNS_FAMILY,
]


# Теперь реестр хранит DTO, а не словари
_FAMILY_REGISTRY: dict[str, MonsterFamilyDTO] = {}
_MONSTER_TEMPLATE_REGISTRY: dict[str, MonsterVariantDTO] = {}
_INITIALIZED = False


def _init_monster_registry():
    """
    Загружает сырые словари и валидирует их через Pydantic DTO.
    """
    global _INITIALIZED
    if _INITIALIZED:
        return

    for raw_data in ALL_FAMILIES_RAW:
        try:
            # === ВАЛИДАЦИЯ ===
            # Используем model_validate для рекурсивного парсинга
            family_dto = MonsterFamilyDTO.model_validate(raw_data)

            # Регистрируем семью
            if family_dto.id in _FAMILY_REGISTRY:
                log.warning(f"Duplicate Family ID: {family_dto.id}")
                continue
            _FAMILY_REGISTRY[family_dto.id] = family_dto

            # Регистрируем варианты (они уже тоже DTO)
            for variant in family_dto.variants.values():
                if variant.id in _MONSTER_TEMPLATE_REGISTRY:
                    log.warning(f"Duplicate Variant ID: {variant.id}")
                    continue
                _MONSTER_TEMPLATE_REGISTRY[variant.id] = variant

        except ValidationError as e:
            # Критическая ошибка: конфиг битый. Лучше увидеть это при старте.
            log.error(f"❌ CONFIG ERROR in family {raw_data.get('id', 'UNKNOWN')}: {e}")
            # Можно сделать raise e, если хочешь, чтобы бот падал при ошибке в конфиге

    log.info(f"Registry loaded: {len(_FAMILY_REGISTRY)} starter families, {len(_MONSTER_TEMPLATE_REGISTRY)} variants.")
    _INITIALIZED = True


_init_monster_registry()


# --- Public API теперь возвращает DTO ---


def get_family_config(family_id: str) -> MonsterFamilyDTO | None:
    return _FAMILY_REGISTRY.get(family_id)


def get_monster_template(variant_id: str) -> MonsterVariantDTO | None:
    return _MONSTER_TEMPLATE_REGISTRY.get(variant_id)


def get_available_variants_for_tier(family_id: str, tier: int) -> list[str]:
    family = _FAMILY_REGISTRY.get(family_id)
    if not family:
        return []

    # Работаем с DTO через точку
    return [var.id for var in family.variants.values() if var.min_tier <= tier <= var.max_tier]


def get_available_variants_for_tier_window(family_id: str, tier: int, radius: int = 1) -> list[str]:
    family = _FAMILY_REGISTRY.get(family_id)
    if not family:
        return []

    min_tier = max(0, tier - radius)
    max_tier = min(7, tier + radius)
    return [var.id for var in family.variants.values() if var.min_tier <= max_tier and var.max_tier >= min_tier]


def get_available_variants_for_family_tier(family_id: str, tier: int) -> list[str]:
    family = _FAMILY_REGISTRY.get(family_id)
    if not family:
        return []

    max_tier = min(7, tier + 1)
    return [var.id for var in family.variants.values() if var.min_tier <= max_tier and var.max_tier >= 0]


def get_starter_family_ids() -> tuple[str, ...]:
    return STARTER_FAMILY_IDS


def get_all_family_configs() -> dict[str, MonsterFamilyDTO]:
    return dict(_FAMILY_REGISTRY)
