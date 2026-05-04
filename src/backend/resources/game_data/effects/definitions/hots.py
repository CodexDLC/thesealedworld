from src.backend.resources.game_data.effects.schemas import EffectDTO, EffectType

HOT_EFFECTS = [
    # REGEN HP (Nature)
    EffectDTO(
        effect_id="hot_regen_hp",
        name_en="Regeneration",
        name_ru="Регенерация",
        type=EffectType.HOT,
        duration=3,
        resource_impact={"hp": 1},  # Base +1. Power 10 -> +10 HP.
        tags=["hot", "regen", "nature", "healing"],
        description="Восстановление здоровья.",
    ),
    # REGEN MANA (Arcane)
    EffectDTO(
        effect_id="hot_regen_en",
        name_en="Clarity",
        name_ru="Ясность",
        type=EffectType.HOT,
        duration=3,
        resource_impact={"en": 1},
        tags=["hot", "clarity", "arcane"],
        description="Восстановление энергии.",
    ),
]
