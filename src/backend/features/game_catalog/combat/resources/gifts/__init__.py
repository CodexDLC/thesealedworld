from collections import defaultdict

from loguru import logger as log

from src.backend.features.game_catalog.combat.resources.gifts.definitions.darkness import DARKNESS_GIFTS
from src.backend.features.game_catalog.combat.resources.gifts.definitions.fire import FIRE_GIFTS
from src.backend.features.game_catalog.combat.resources.gifts.definitions.light import LIGHT_GIFTS
from src.backend.features.game_catalog.combat.resources.gifts.definitions.nature import NATURE_GIFTS
from src.backend.features.game_catalog.combat.resources.gifts.definitions.water import WATER_GIFTS
from src.backend.features.game_catalog.combat.resources.gifts.schemas import GiftDTO, GiftSchool
from src.backend.features.game_catalog.combat.resources.gifts.xp_config import GIFT_LEVELING

# ==========================================
# ГЛОБАЛЬНЫЕ РЕЕСТРЫ (In-Memory DB)
# ==========================================

GIFT_REGISTRY: dict[str, GiftDTO] = {}
GIFTS_BY_SCHOOL: dict[GiftSchool, list[GiftDTO]] = defaultdict(list)
_INITIALIZED = False


def _register_gifts(gift_list: list[GiftDTO]) -> None:
    for gift in gift_list:
        if gift.gift_id in GIFT_REGISTRY:
            log.warning(f"GiftLibrary | Duplicate gift ID: '{gift.gift_id}'. Overwriting.")

        GIFT_REGISTRY[gift.gift_id] = gift
        GIFTS_BY_SCHOOL[gift.school].append(gift)


def _initialize_library() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return

    log.info("GiftLibrary | Initializing Gift Library...")

    all_gifts = [FIRE_GIFTS, WATER_GIFTS, LIGHT_GIFTS, DARKNESS_GIFTS, NATURE_GIFTS]

    count = 0
    for group in all_gifts:
        _register_gifts(group)
        count += len(group)

    log.info(f"GiftLibrary | Initialization complete. Loaded {count} gifts.")
    _INITIALIZED = True


# ==========================================
# PUBLIC API
# ==========================================


def get_gift_config(gift_id: str) -> GiftDTO | None:
    return GIFT_REGISTRY.get(gift_id)


def get_all_gifts() -> list[GiftDTO]:
    return list(GIFT_REGISTRY.values())


def get_gifts_by_school(school: GiftSchool) -> list[GiftDTO]:
    return GIFTS_BY_SCHOOL.get(school, [])


def get_gift_level_info(level: int) -> dict | None:
    return GIFT_LEVELING.get(level)


# Auto-init
_initialize_library()
