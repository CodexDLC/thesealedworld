from src.backend.resources.game_data.gifts.schemas import GiftDTO, GiftSchool

NATURE_GIFTS = [
    GiftDTO(
        gift_id="gift_beastmaster",
        name_ru="Звериная Душа",
        school=GiftSchool.NATURE,
        description="Животные Аномалии не трогают тебя. Ты можешь подчинять их своей воле.",
        role="Summoner",
        abilities=["tame_beast", "feral_rage"],
    ),
    GiftDTO(
        gift_id="gift_thorns",
        name_ru="Шипы",
        school=GiftSchool.NATURE,
        description="Природа агрессивна. Ты выращиваешь лозы и шипы прямо из земли.",
        role="Control / Damage",
        abilities=["entangle", "thorn_burst"],
    ),
]
