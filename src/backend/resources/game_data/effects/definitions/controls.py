from src.backend.resources.game_data.effects.schemas import ControlInstructionDTO, EffectDTO, EffectType

CONTROL_EFFECTS = [
    # STUN
    EffectDTO(
        effect_id="stun",
        name_en="Stun",
        name_ru="Оглушение",
        type=EffectType.CONTROL,
        duration=1,
        control_logic=ControlInstructionDTO(
            status_name="is_stun",
            source_behavior={"can_act": False},
            target_behavior={"can_dodge": False, "force_hit": True},
        ),
        tags=["control", "stun", "physical"],
        description="Пропуск хода. Нельзя уклоняться.",
    ),
    # SLEEP
    EffectDTO(
        effect_id="sleep",
        name_en="Sleep",
        name_ru="Сон",
        type=EffectType.CONTROL,
        duration=3,
        control_logic=ControlInstructionDTO(
            status_name="is_sleep",
            source_behavior={"can_act": False},
            target_behavior={"can_dodge": False, "force_crit": True},  # По спящему крит
        ),
        tags=["control", "sleep", "mental"],
        description="Спит. Любой урон будит (логика пробуждения в Resolver).",
    ),
    # KNOCKDOWN
    EffectDTO(
        effect_id="knockdown",
        name_en="Knockdown",
        name_ru="Сбит с ног",
        type=EffectType.CONTROL,
        duration=1,
        control_logic=ControlInstructionDTO(
            status_name="is_knockdown",
            source_behavior={"can_act": True},  # Можно бить, но лежа? (пока True)
            target_behavior={"can_dodge": False},
        ),
        tags=["control", "knockdown", "physical"],
        description="Сбит с ног. Нельзя уклоняться.",
    ),
    # DISARM
    EffectDTO(
        effect_id="disarm",
        name_en="Disarm",
        name_ru="Обезоруживание",
        type=EffectType.CONTROL,
        duration=2,
        control_logic=ControlInstructionDTO(
            status_name="is_disarmed", source_behavior={"can_use_weapon": False}, target_behavior={}
        ),
        tags=["control", "disarm", "physical"],
        description="Нельзя использовать оружие.",
    ),
    # SILENCE
    EffectDTO(
        effect_id="silence",
        name_en="Silence",
        name_ru="Безмолвие",
        type=EffectType.CONTROL,
        duration=2,
        control_logic=ControlInstructionDTO(
            status_name="is_silenced", source_behavior={"can_cast_spell": False}, target_behavior={}
        ),
        tags=["control", "silence", "magical"],
        description="Нельзя использовать магию.",
    ),
]
