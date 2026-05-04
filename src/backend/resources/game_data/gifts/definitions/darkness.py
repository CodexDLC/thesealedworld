from src.backend.resources.game_data.gifts.schemas import GiftDTO, GiftSchool

DARKNESS_GIFTS = [
    GiftDTO(
        gift_id="gift_shadow_assassin",
        name_ru="Тень",
        school=GiftSchool.DARKNESS,
        description="Ты сливаешься с тенью. Удары из невидимости и обман зрения.",
        role="Stealth / Burst",
        abilities=["shadow_step", "backstab_bonus"],
    ),
    GiftDTO(
        gift_id="gift_necrosis",
        name_ru="Некроз",
        school=GiftSchool.DARKNESS,
        description="Тьма иссушает врагов, передавая их жизненные силы тебе.",
        role="Drain / Debuff",
        abilities=["life_drain", "weaken"],
    ),
]
