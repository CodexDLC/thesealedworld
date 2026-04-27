from src.backend.resources.game_data.gifts.schemas import GiftDTO, GiftSchool

LIGHT_GIFTS = [
    GiftDTO(
        gift_id="gift_paladin",
        name_ru="Защитник Света",
        school=GiftSchool.LIGHT,
        description="Свет уплотняется, создавая барьеры. Дар для тех, кто стоит в авангарде.",
        role="Tank / Support",
        abilities=["light_shield", "blessing"],
    ),
    GiftDTO(
        gift_id="gift_purifier",
        name_ru="Очиститель",
        school=GiftSchool.LIGHT,
        description="Агрессивный свет, выжигающий скверну. Особо эффективен против порождений Рифтов.",
        role="Damage vs Undead",
        abilities=["smite", "holy_beam"],
    ),
]
