from loguru import logger as log
from pydantic import ValidationError

from src.shared.schemas.monster_dto import MonsterFamilyDTO, MonsterVariantDTO

# --- 1. ИМПОРТ ВСЕХ ФАЙЛОВ СЕМЕЙСТВ ---
from .families.angels import ANGELS_FAMILY
from .families.ants import ANTS_FAMILY
from .families.bandits import BANDITS_FAMILY
from .families.dark_elves import DARK_ELVES_FAMILY
from .families.demons import DEMONS_FAMILY
from .families.dragons import DRAGONS_FAMILY
from .families.elementals import ELEMENTALS_FAMILY
from .families.flying import FLYING_FAMILY
from .families.goblins import GOBLINS_FAMILY
from .families.golems import GOLEMS_FAMILY
from .families.insects import INSECTS_FAMILY
from .families.orcs import ORCS_FAMILY
from .families.rats import RATS_FAMILY
from .families.snakes import SNAKES_FAMILY
from .families.spiders import SPIDERS_FAMILY
from .families.undead import UNDEAD_FAMILY
from .families.vampires import VAMPIRES_FAMILY
from .families.werewolves import WEREWOLVES_FAMILY
from .families.wolves import WOLVES_FAMILY
from .monster_structs import MonsterFamily

ALL_FAMILIES_RAW: list[MonsterFamily] = [
    ANGELS_FAMILY,
    ANTS_FAMILY,
    BANDITS_FAMILY,
    DARK_ELVES_FAMILY,
    DEMONS_FAMILY,
    DRAGONS_FAMILY,
    ELEMENTALS_FAMILY,
    FLYING_FAMILY,
    GOBLINS_FAMILY,
    GOLEMS_FAMILY,
    INSECTS_FAMILY,
    ORCS_FAMILY,
    RATS_FAMILY,
    SNAKES_FAMILY,
    SPIDERS_FAMILY,
    UNDEAD_FAMILY,
    VAMPIRES_FAMILY,
    WEREWOLVES_FAMILY,
    WOLVES_FAMILY,
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

    log.info(f"✅ Registry loaded: {len(_FAMILY_REGISTRY)} Families, {len(_MONSTER_TEMPLATE_REGISTRY)} Variants.")
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
