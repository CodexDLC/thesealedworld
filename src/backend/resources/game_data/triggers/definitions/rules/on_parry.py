from src.backend.resources.game_data.triggers.schemas import TriggerDTO

ON_PARRY_RULES = [
    # --- ON_PARRY (Успех) ---
    TriggerDTO(
        id="disarm_on_parry",
        name_ru="Обезоруживание (Парирование)",
        description_ru="Успешное парирование обезоруживает врага.",
        event="ON_PARRY",
        chance=0.5,
        mutations={
            "add_effect": {"id": "disarm"},
        },
    ),
    TriggerDTO(
        id="counter_on_parry",
        name_ru="Контратака (Парирование)",
        description_ru="Успешное парирование активирует контратаку.",
        event="ON_PARRY",
        chance=1.0,
        mutations={
            "state.allow_counter_on_parry": True,  # Разрешаем проверку
            "state.check_counter": True,  # Запускаем проверку
        },
    ),
]
