from src.backend.resources.game_data.gifts.schemas import GiftDTO, GiftSchool

WATER_GIFTS = [
    GiftDTO(
        gift_id="gift_calm_water",
        name_ru="Спокойная Вода",
        school=GiftSchool.WATER,
        description="Вода течет и заживляет. Лучший дар для поддержки группы и регенерации.",
        role="Healer",
        abilities=["heal_wave", "cleanse"],
    ),
    GiftDTO(
        gift_id="gift_typhoon",
        name_ru="Тайфун",
        school=GiftSchool.WATER,
        description="Вода как молот. Ты управляешь давлением и потоками, сбивая врагов с ног.",
        role="Control / Damage",
        abilities=["water_jet", "tsunami"],
    ),
    GiftDTO(
        gift_id="gift_venom_blood",
        name_ru="Ядовитая Кровь",
        school=GiftSchool.WATER,
        description="Ты управляешь токсинами и кислотами. Враги умирают медленно, но гарантированно.",
        role="DoT (Damage over Time)",
        abilities=["poison_cloud", "acid_splash"],
    ),
]
