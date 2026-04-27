from src.backend.resources.game_data.triggers.schemas import TriggerDTO

ON_CONTROL_RULES = [
    # Пример: Стан при попадании (для булав или финтов)
    TriggerDTO(
        id="stun_on_hit",
        name_ru="Оглушение (Удар)",
        description_ru="Успешное попадание может оглушить цель.",
        event="ON_CHECK_CONTROL",
        chance=0.5,  # 50% шанс
        mutations={
            "add_effect": {"id": "stun"},
        },
    ),
    # Пример: Кровотечение при попадании (для финтов)
    TriggerDTO(
        id="bleed_on_hit",
        name_ru="Кровотечение (Удар)",
        description_ru="Успешное попадание вызывает кровотечение.",
        event="ON_CHECK_CONTROL",
        chance=1.0,
        mutations={
            "add_effect": {"id": "bleed"},
        },
    ),
    # Пример: Маркер уворота (для луков)
    TriggerDTO(
        id="evasive_shot",
        name_ru="Уклонение (Выстрел)",
        description_ru="Попадание дает возможность гарантированно уклониться.",
        event="ON_CHECK_CONTROL",
        chance=1.0,
        mutations={
            "add_effect": {"id": "marker_evasion"},
        },
    ),
]
