from collections import defaultdict

from loguru import logger as log

from src.backend.features.game_catalog.combat.resources.gifts.definitions.darkness import (
    DARKNESS_GIFTS_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.gifts.definitions.fire import FIRE_GIFTS_CATALOG
from src.backend.features.game_catalog.combat.resources.gifts.definitions.light import LIGHT_GIFTS_CATALOG
from src.backend.features.game_catalog.combat.resources.gifts.definitions.nature import NATURE_GIFTS_CATALOG
from src.backend.features.game_catalog.combat.resources.gifts.definitions.water import WATER_GIFTS_CATALOG
from src.backend.features.game_catalog.combat.resources.gifts.schemas import (
    GiftCatalogEntryDTO,
    GiftSchool,
)
from src.backend.features.game_catalog.combat.resources.gifts.xp_config import GIFT_LEVELING

# ==========================================
# ГЛОБАЛЬНЫЕ РЕЕСТРЫ (In-Memory DB)
# ==========================================

GIFT_CATALOG_REGISTRY: dict[str, GiftCatalogEntryDTO] = {}
GIFT_CATALOG_BY_KEY: dict[str, GiftCatalogEntryDTO] = {}
GIFTS_BY_SCHOOL: dict[GiftSchool, list[GiftCatalogEntryDTO]] = defaultdict(list)
_INITIALIZED = False


def _register_gifts(gift_entries: list[GiftCatalogEntryDTO]) -> None:
    for entry in gift_entries:
        gift = entry.technical
        if gift.gift_id in GIFT_CATALOG_REGISTRY:
            log.bind(gift_id=gift.gift_id).warning("GiftLibraryDuplicateGiftId")

        GIFT_CATALOG_REGISTRY[gift.gift_id] = entry
        GIFT_CATALOG_BY_KEY[entry.key] = entry
        GIFTS_BY_SCHOOL[gift.school].append(entry)


def _initialize_library() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return

    log.info("GiftLibraryInitializing")

    all_gifts = [
        list(FIRE_GIFTS_CATALOG.values()),
        list(WATER_GIFTS_CATALOG.values()),
        list(LIGHT_GIFTS_CATALOG.values()),
        list(DARKNESS_GIFTS_CATALOG.values()),
        list(NATURE_GIFTS_CATALOG.values()),
    ]

    count = 0
    for group in all_gifts:
        _register_gifts(group)
        count += len(group)

    log.bind(gift_count=count).info("GiftLibraryLoaded")
    _INITIALIZED = True


# ==========================================
# PUBLIC API
# ==========================================


def get_gift_catalog_entries_by_school(school: GiftSchool) -> list[GiftCatalogEntryDTO]:
    return GIFTS_BY_SCHOOL.get(school, [])


def get_gift_catalog_entry(gift_id: str) -> GiftCatalogEntryDTO | None:
    return GIFT_CATALOG_REGISTRY.get(gift_id)


def get_gift_catalog_entry_by_key(catalog_key: str) -> GiftCatalogEntryDTO | None:
    return GIFT_CATALOG_BY_KEY.get(catalog_key)


def get_all_gift_catalog_entries() -> list[GiftCatalogEntryDTO]:
    return list(GIFT_CATALOG_REGISTRY.values())


def get_gift_level_info(level: int) -> dict | None:
    return GIFT_LEVELING.get(level)


# Auto-init
_initialize_library()
