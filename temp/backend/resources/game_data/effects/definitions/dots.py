from src.backend.resources.game_data.effects.schemas import EffectDTO, EffectType

DOT_EFFECTS = [
    # POISON (Nature)
    EffectDTO(
        effect_id="dot_poison",
        name_en="Poison",
        name_ru="Яд",
        type=EffectType.DOT,
        duration=3,
        resource_impact={"hp": -1},  # Base -1. Power 10 -> -10 HP.
        tags=["dot", "poison", "nature"],
        description="Яд наносит урон каждый ход.",
    ),
    # BLEED (Physical)
    EffectDTO(
        effect_id="dot_bleed",
        name_en="Bleeding",
        name_ru="Кровотечение",
        type=EffectType.DOT,
        duration=3,
        resource_impact={"hp": -1},
        tags=["dot", "bleed", "physical"],
        description="Рана кровоточит.",
    ),
    # BURN (Fire)
    EffectDTO(
        effect_id="dot_burn",
        name_en="Burn",
        name_ru="Ожог",
        type=EffectType.DOT,
        duration=3,
        resource_impact={"hp": -1},
        tags=["dot", "burn", "fire"],
        description="Огонь обжигает плоть.",
    ),
]
