from src.backend.resources.game_data.triggers.schemas import TriggerDTO

ON_ACCURACY_RULES = [
    # Пример: Гарантированное попадание (отключает уворот)
    TriggerDTO(
        id="true_strike",
        name_ru="Верный удар",
        description_ru="Игнорирует уклонение цели.",
        event="ON_ACCURACY_CHECK",
        chance=1.0,
        mutations={
            "force.hit_evasion": True,  # Враг не может увернуться
        },
    ),
    # Пример: Ярость при промахе
    TriggerDTO(
        id="rage_on_miss",
        name_ru="Ярость берсерка",
        description_ru="Промах увеличивает урон следующей атаки (через токен).",
        event="ON_MISS",
        chance=1.0,
        mutations={
            "tokens_awarded_attacker": ["RAGE_TOKEN"],  # Пример
        },
    ),
]
