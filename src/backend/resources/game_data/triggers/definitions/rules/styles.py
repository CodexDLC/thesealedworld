from src.backend.resources.game_data.triggers.schemas import TriggerDTO

STYLE_RULES = [
    # --- 1. ONE-HANDED (Flow) ---
    TriggerDTO(
        id="style_1h_flow",
        name_ru="Поток (Стиль)",
        description_ru="Сохраняет тактические токены при успешном действии.",
        event="ON_ACCURACY_CHECK",  # Или ON_HIT
        chance=0.25,
        mutations={
            # Инструкция для AbilityService вернуть токены
            "add_effect": {"id": "refund_tactics"},
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
            # 1. Игнор брони (здесь и сейчас)
            "formula.can_pierce": True,
            # 2. Ослабление защиты (здесь и сейчас)
            "formula.parry_halved": True,
            "formula.block_halved": True,
            # Можно добавить ignore_block_cap, если нужно
        },
    ),
    # --- 3. SHIELD (Reflect) ---
    TriggerDTO(
        id="style_shield_reflect",
        name_ru="Отражение (Стиль)",
        description_ru="При блоке возвращает часть урона врагу.",
        event="ON_BLOCK",
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
