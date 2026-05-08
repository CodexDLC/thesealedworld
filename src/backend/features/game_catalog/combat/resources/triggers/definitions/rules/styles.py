from src.backend.features.game_catalog.combat.resources.triggers.schemas import TriggerDTO

STYLE_RULES = [
    # --- 1. ONE-HANDED (Flow) ---
    TriggerDTO(
        id="style_1h_flow",
        name_ru="Поток (Стиль)",
        description_ru="С шансом сохраняет темп: возвращает стоимость использованного финта.",
        event="ON_ACCURACY_CHECK",  # Или ON_HIT
        chance=0.25,
        mutations={
            "chain_events.preserve_feint": True,
        },
    ),
    # --- 2. TWO-HANDED (Ignore) ---
    TriggerDTO(
        id="style_2h_ignore",
        name_ru="Пробитие (Стиль)",
        description_ru="Игнорирует броню и ослабляет защиту врага.",
        event="ON_ACCURACY_CHECK",
        chance=0.25,
        mutations={
            "formula.evasion_halved": True,
            "formula.parry_halved": True,
            "formula.block_halved": True,
        },
    ),
    # --- 3. SHIELD (Reflect) ---
    TriggerDTO(
        id="style_shield_reflect",
        name_ru="Отражение (Стиль)",
        description_ru="При провале блока частично гасит удар и готовит отражение.",
        event="ON_BLOCK_FAIL",
        chance=0.25,
        mutations={
            # Включаем механику отражения в Резолвере
            "state.partial_absorb_reflect": True,
        },
    ),
    # --- 4. DUAL WIELD (Extra Attack) ---
    TriggerDTO(
        id="style_dual_extra",
        name_ru="Доп. атака (Стиль)",
        description_ru="Мгновенная атака второй рукой.",
        event="ON_ACCURACY_CHECK",
        chance=0.25,
        mutations={
            "chain_events.trigger_offhand_attack": True,
        },
    ),
]
