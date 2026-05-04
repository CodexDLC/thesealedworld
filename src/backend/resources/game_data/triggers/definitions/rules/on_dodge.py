from src.backend.resources.game_data.triggers.schemas import TriggerDTO

ON_DODGE_RULES = [
    # --- ON_DODGE (Успех) ---
    TriggerDTO(
        id="counter_on_dodge",
        name_ru="Контратака (Уворот)",
        description_ru="Успешное уклонение активирует контратаку.",
        event="ON_DODGE",
        chance=1.0,
        mutations={
            "chain_events.trigger_counter_attack": True,
        },
    ),
    # --- ON_DODGE_FAIL (Неудача) ---
    # Пример: Если не увернулся, получи больше урона (для берсерка?)
]
