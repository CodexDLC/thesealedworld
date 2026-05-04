from src.backend.resources.game_data.effects.schemas import EffectDTO, EffectType

BUFF_EFFECTS = [
    # --- ATTRIBUTES (Base 1.0) ---
    EffectDTO(
        effect_id="buff_str",
        name_en="Strength Buff",
        name_ru="Усиление Силы",
        type=EffectType.BUFF,
        duration=3,
        raw_modifiers={"strength": 1.0},  # Power 5 -> +5 Str
        tags=["buff", "attribute", "physical"],
        description="Увеличивает Силу.",
    ),
    EffectDTO(
        effect_id="buff_dex",
        name_en="Dexterity Buff",
        name_ru="Усиление Ловкости",
        type=EffectType.BUFF,
        duration=3,
        raw_modifiers={"dexterity": 1.0},
        tags=["buff", "attribute", "physical"],
        description="Увеличивает Ловкость.",
    ),
    EffectDTO(
        effect_id="buff_int",
        name_en="Intelligence Buff",
        name_ru="Усиление Интеллекта",
        type=EffectType.BUFF,
        duration=3,
        raw_modifiers={"intelligence": 1.0},
        tags=["buff", "attribute", "magical"],
        description="Увеличивает Интеллект.",
    ),
    EffectDTO(
        effect_id="buff_end",
        name_en="Endurance Buff",
        name_ru="Усиление Выносливости",
        type=EffectType.BUFF,
        duration=3,
        raw_modifiers={"endurance": 1.0},
        tags=["buff", "attribute", "physical"],
        description="Увеличивает Выносливость.",
    ),
    # --- DEFENSE (Base 1.0 / 0.01) ---
    EffectDTO(
        effect_id="buff_armor",
        name_en="Armor Buff",
        name_ru="Усиление Брони",
        type=EffectType.BUFF,
        duration=3,
        raw_modifiers={"armor": 1.0},  # Power 10 -> +10 Armor
        tags=["buff", "defense", "physical"],
        description="Увеличивает Броню.",
    ),
    EffectDTO(
        effect_id="buff_evasion",
        name_en="Evasion Buff",
        name_ru="Усиление Уклонения",
        type=EffectType.BUFF,
        duration=3,
        raw_modifiers={"evasion": 0.01},  # Power 10 -> +10% (0.1)
        tags=["buff", "defense", "air"],
        description="Увеличивает шанс уклонения.",
    ),
    # --- OFFENSE (Base 0.01) ---
    EffectDTO(
        effect_id="buff_accuracy",
        name_en="Accuracy Buff",
        name_ru="Усиление Точности",
        type=EffectType.BUFF,
        duration=3,
        raw_modifiers={"accuracy": 0.01},  # Power 10 -> +10%
        tags=["buff", "offense"],
        description="Увеличивает точность.",
    ),
    EffectDTO(
        effect_id="buff_crit",
        name_en="Crit Buff",
        name_ru="Усиление Крита",
        type=EffectType.BUFF,
        duration=3,
        raw_modifiers={"crit_chance": 0.01},  # Power 10 -> +10%
        tags=["buff", "offense"],
        description="Увеличивает шанс крита.",
    ),
    EffectDTO(
        effect_id="buff_phys_dmg",
        name_en="Phys Dmg Buff",
        name_ru="Усиление Физ. Урона",
        type=EffectType.BUFF,
        duration=3,
        raw_modifiers={"physical_damage_bonus": 1.0},  # Power 10 -> +10 Dmg
        tags=["buff", "offense", "physical"],
        description="Увеличивает физический урон.",
    ),
]
