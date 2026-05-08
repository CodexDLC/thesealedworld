from src.backend.features.game_catalog.combat.resources.gifts.schemas import (
    GiftSchool,
    GiftTechnicalDTO,
    build_gift_catalog_entry,
)

NATURE_GIFTS_TECHNICAL = {
    "gift_beastmaster": GiftTechnicalDTO(
        gift_id="gift_beastmaster",
        school=GiftSchool.NATURE,
        role="Summoner",
        abilities=["tame_beast", "feral_rage"],
    ),
    "gift_thorns": GiftTechnicalDTO(
        gift_id="gift_thorns",
        school=GiftSchool.NATURE,
        role="Control / Damage",
        abilities=["entangle", "thorn_burst"],
    ),
}

NATURE_GIFTS_CATALOG = {
    "gift_beastmaster": build_gift_catalog_entry(
        technical=NATURE_GIFTS_TECHNICAL["gift_beastmaster"],
        display_name="Звериная Душа",
        short_description="Животные Аномалии не трогают тебя. Ты можешь подчинять их своей воле.",
    ),
    "gift_thorns": build_gift_catalog_entry(
        technical=NATURE_GIFTS_TECHNICAL["gift_thorns"],
        display_name="Шипы",
        short_description="Природа агрессивна. Ты выращиваешь лозы и шипы прямо из земли.",
    ),
}

NATURE_GIFTS = [entry.technical for entry in NATURE_GIFTS_CATALOG.values()]
