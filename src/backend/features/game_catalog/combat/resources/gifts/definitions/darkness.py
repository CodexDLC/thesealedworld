from src.backend.features.game_catalog.combat.resources.gifts.schemas import (
    GiftSchool,
    GiftTechnicalDTO,
    build_gift_catalog_entry,
)

DARKNESS_GIFTS_TECHNICAL = {
    "gift_shadow_assassin": GiftTechnicalDTO(
        gift_id="gift_shadow_assassin",
        school=GiftSchool.DARKNESS,
        role="Stealth / Burst",
        abilities=["shadow_step", "backstab_bonus"],
    ),
    "gift_necrosis": GiftTechnicalDTO(
        gift_id="gift_necrosis",
        school=GiftSchool.DARKNESS,
        role="Drain / Debuff",
        abilities=["life_drain", "weaken"],
    ),
}

DARKNESS_GIFTS_CATALOG = {
    "gift_shadow_assassin": build_gift_catalog_entry(
        technical=DARKNESS_GIFTS_TECHNICAL["gift_shadow_assassin"],
        display_name="Тень",
        short_description="Ты сливаешься с тенью. Удары из невидимости и обман зрения.",
    ),
    "gift_necrosis": build_gift_catalog_entry(
        technical=DARKNESS_GIFTS_TECHNICAL["gift_necrosis"],
        display_name="Некроз",
        short_description="Тьма иссушает врагов, передавая их жизненные силы тебе.",
    ),
}

DARKNESS_GIFTS = [entry.technical for entry in DARKNESS_GIFTS_CATALOG.values()]
