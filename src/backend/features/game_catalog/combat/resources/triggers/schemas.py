from typing import Any

from pydantic import BaseModel, Field


class TriggerDTO(BaseModel):
    """
    Единое определение триггера.
    Содержит и данные для UI (тексты), и данные для логики (правила).
    """

    # === UI / META ===
    id: str  # Уникальный ID (например, "trigger_bleed")
    name_ru: str  # Название ("Кровотечение")
    description_ru: str  # Описание ("При крите накладывает...")
    icon: str | None = None  # Иконка ("bleed.png")

    # === LOGIC (Combat Resolver) ===
    event: str  # Событие активации ("ON_CRIT", "ON_HIT")
    chance: float = 1.0  # Шанс срабатывания (0.0 - 1.0)

    # Мутации контекста боя.
    # Могут менять флаги (crit_damage_boost), модификаторы (weapon_effect_value)
    # или выставлять флаги для AbilityService (apply_bleed).
    mutations: dict[str, Any] = Field(default_factory=dict)
