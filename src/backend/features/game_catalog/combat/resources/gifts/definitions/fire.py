from src.backend.features.game_catalog.combat.resources.common.descriptions import CombatEventTextSetDTO
from src.backend.features.game_catalog.combat.resources.gifts.schemas import (
    GiftSchool,
    GiftTechnicalDTO,
    build_gift_catalog_entry,
)

FIRE_GIFTS_TECHNICAL = {
    "gift_true_fire": GiftTechnicalDTO(
        gift_id="gift_true_fire",
        school=GiftSchool.FIRE,
        role="Damage Dealer",
        abilities=["fireball", "flame_thrower"],
    ),
    "gift_inferno": GiftTechnicalDTO(
        gift_id="gift_inferno",
        school=GiftSchool.FIRE,
        role="AOE Damage",
        abilities=["explosion", "burning_aura"],
    ),
    "gift_dragon_flame": GiftTechnicalDTO(
        gift_id="gift_dragon_flame",
        school=GiftSchool.FIRE,
        role="Tank / Melee",
        abilities=["magma_skin", "fire_breath"],
    ),
}

FIRE_GIFTS_CATALOG = {
    "gift_true_fire": build_gift_catalog_entry(
        technical=FIRE_GIFTS_TECHNICAL["gift_true_fire"],
        display_name="Истинное Пламя",
        short_description="Твой огонь не требует топлива. Он горит даже на воде. Классический боевой пирокинез.",
        event_texts=CombatEventTextSetDTO(
            use=["Дар {gift} отзывается жаром в руках {source}."],
            hit=["Дар {gift} помогает {source} поразить {target}."],
            crit=["Дар {gift} вспыхивает особенно ярко и поражает {target}."],
            apply_effect=["Дар {gift} оставляет на {target} эффект {effect}."],
            area_use=["{source} раскрывает жар дара {gift}."],
            area_result=["Пламя дара {gift} расходится по {targets_count} целям."],
            no_resource=["Дар {gift} гаснет в руках {source}: ресурса не хватает."],
        ),
    ),
    "gift_inferno": build_gift_catalog_entry(
        technical=FIRE_GIFTS_TECHNICAL["gift_inferno"],
        display_name="Инферно",
        short_description="Ты — эпицентр взрыва. Твой дар нестабилен и наносит огромный урон по площади.",
    ),
    "gift_dragon_flame": build_gift_catalog_entry(
        technical=FIRE_GIFTS_TECHNICAL["gift_dragon_flame"],
        display_name="Пламя Дракона",
        short_description="Твоя кожа тверда, а огонь густой, как лава. Дар усиливает ближний бой.",
    ),
}

FIRE_GIFTS = [entry.technical for entry in FIRE_GIFTS_CATALOG.values()]
