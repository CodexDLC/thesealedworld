from src.backend.resources.game_data.effects.schemas import EffectDTO, EffectType

DEBUFF_EFFECTS = [
    # --- ATTRIBUTES (Base -1.0) ---
    EffectDTO(
        effect_id="debuff_str",
        name_en="Strength Debuff",
        name_ru="Ослабление Силы",
        type=EffectType.DEBUFF,
        duration=3,
        raw_modifiers={"strength": -1.0},  # Power 5 -> -5 Str
        tags=["debuff", "attribute", "curse"],
        description="Снижает Силу.",
    ),
    # --- DEFENSE (Base -1.0 / -0.01) ---
    EffectDTO(
        effect_id="debuff_armor",
        name_en="Armor Debuff",
        name_ru="Ослабление Брони",
        type=EffectType.DEBUFF,
        duration=3,
        raw_modifiers={"armor": -1.0},  # Power 10 -> -10 Armor
        tags=["debuff", "defense", "physical"],
        description="Снижает Броню.",
    ),
    EffectDTO(
        effect_id="debuff_evasion",
        name_en="Evasion Debuff",
        name_ru="Ослабление Уклонения",
        type=EffectType.DEBUFF,
        duration=3,
        raw_modifiers={"evasion": -0.01},  # Power 10 -> -10%
        tags=["debuff", "defense", "ice"],
        description="Снижает уклонение.",
    ),
    # --- OFFENSE (Base -0.01) ---
    EffectDTO(
        effect_id="debuff_accuracy",
        name_en="Accuracy Debuff",
        name_ru="Ослабление Точности",
        type=EffectType.DEBUFF,
        duration=3,
        raw_modifiers={"accuracy": -0.01},  # Power 20 -> -20%
        tags=["debuff", "offense", "physical"],
        description="Снижает точность.",
    ),
]
