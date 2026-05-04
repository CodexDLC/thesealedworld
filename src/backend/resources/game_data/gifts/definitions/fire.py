from src.backend.resources.game_data.gifts.schemas import GiftDTO, GiftSchool

FIRE_GIFTS = [
    GiftDTO(
        gift_id="gift_true_fire",
        name_ru="Истинное Пламя",
        school=GiftSchool.FIRE,
        description="Твой огонь не требует топлива. Он горит даже на воде. Классический боевой пирокинез.",
        role="Damage Dealer",
        abilities=["fireball", "flame_thrower"],
    ),
    GiftDTO(
        gift_id="gift_inferno",
        name_ru="Инферно",
        school=GiftSchool.FIRE,
        description="Ты — эпицентр взрыва. Твой дар нестабилен и наносит огромный урон по площади.",
        role="AOE Damage",
        abilities=["explosion", "burning_aura"],
    ),
    GiftDTO(
        gift_id="gift_dragon_flame",
        name_ru="Пламя Дракона",
        school=GiftSchool.FIRE,
        description="Твоя кожа тверда, а огонь густой, как лава. Дар усиливает ближний бой.",
        role="Tank / Melee",
        abilities=["magma_skin", "fire_breath"],
    ),
]
