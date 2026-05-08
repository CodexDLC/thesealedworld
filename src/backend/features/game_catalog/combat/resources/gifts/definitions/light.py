from src.backend.features.game_catalog.combat.resources.gifts.schemas import (
    GiftSchool,
    GiftTechnicalDTO,
    build_gift_catalog_entry,
)

LIGHT_GIFTS_TECHNICAL = {
    "gift_paladin": GiftTechnicalDTO(
        gift_id="gift_paladin",
        school=GiftSchool.LIGHT,
        role="Tank / Support",
        abilities=["light_shield", "blessing"],
    ),
    "gift_purifier": GiftTechnicalDTO(
        gift_id="gift_purifier",
        school=GiftSchool.LIGHT,
        role="Damage vs Undead",
        abilities=["smite", "holy_beam"],
    ),
}

LIGHT_GIFTS_CATALOG = {
    "gift_paladin": build_gift_catalog_entry(
        technical=LIGHT_GIFTS_TECHNICAL["gift_paladin"],
        display_name="Защитник Света",
        short_description="Свет уплотняется, создавая барьеры. Дар для тех, кто стоит в авангарде.",
    ),
    "gift_purifier": build_gift_catalog_entry(
        technical=LIGHT_GIFTS_TECHNICAL["gift_purifier"],
        display_name="Очиститель",
        short_description="Агрессивный свет, выжигающий скверну. Особо эффективен против порождений Рифтов.",
    ),
}

LIGHT_GIFTS = [entry.technical for entry in LIGHT_GIFTS_CATALOG.values()]
