from src.backend.features.game_catalog.combat.resources.gifts.schemas import (
    GiftSchool,
    GiftTechnicalDTO,
    build_gift_catalog_entry,
)

WATER_GIFTS_TECHNICAL = {
    "gift_calm_water": GiftTechnicalDTO(
        gift_id="gift_calm_water",
        school=GiftSchool.WATER,
        role="Healer",
        abilities=["heal_wave", "cleanse"],
    ),
    "gift_typhoon": GiftTechnicalDTO(
        gift_id="gift_typhoon",
        school=GiftSchool.WATER,
        role="Control / Damage",
        abilities=["water_jet", "tsunami"],
    ),
    "gift_venom_blood": GiftTechnicalDTO(
        gift_id="gift_venom_blood",
        school=GiftSchool.WATER,
        role="DoT (Damage over Time)",
        abilities=["poison_cloud", "acid_splash"],
    ),
}

WATER_GIFTS_CATALOG = {
    "gift_calm_water": build_gift_catalog_entry(
        technical=WATER_GIFTS_TECHNICAL["gift_calm_water"],
        display_name="Спокойная Вода",
        short_description="Вода течет и заживляет. Лучший дар для поддержки группы и регенерации.",
    ),
    "gift_typhoon": build_gift_catalog_entry(
        technical=WATER_GIFTS_TECHNICAL["gift_typhoon"],
        display_name="Тайфун",
        short_description="Вода как молот. Ты управляешь давлением и потоками, сбивая врагов с ног.",
    ),
    "gift_venom_blood": build_gift_catalog_entry(
        technical=WATER_GIFTS_TECHNICAL["gift_venom_blood"],
        display_name="Ядовитая Кровь",
        short_description="Ты управляешь токсинами и кислотами. Враги умирают медленно, но гарантированно.",
    ),
}

WATER_GIFTS = [entry.technical for entry in WATER_GIFTS_CATALOG.values()]
