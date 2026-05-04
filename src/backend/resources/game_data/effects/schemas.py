from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EffectType(str, Enum):
    DOT = "dot"  # Damage Over Time
    HOT = "hot"  # Heal Over Time
    BUFF = "buff"  # Stat Bonus
    DEBUFF = "debuff"  # Stat Penalty
    CONTROL = "control"  # Stun, Sleep, Silence (Logic)


class ControlInstructionDTO(BaseModel):
    """
    Инструкции поведения для эффектов контроля.
    """

    # Имя флага состояния (для UI/AI и проверок)
    # Пример: "is_stun", "is_blind"
    status_name: str

    # Инструкции для Атакующего (если он под этим эффектом)
    # Ключи, которые понимает AbilityService/ContextBuilder.
    # Пример: {"can_act": False} (Стан), {"accuracy_mult": 0.5} (Слепота)
    source_behavior: dict[str, Any] = Field(default_factory=dict)

    # Инструкции для Защитника (если он под этим эффектом)
    # Пример: {"can_dodge": False} (Стан), {"damage_taken_mult": 1.5} (Уязвимость)
    target_behavior: dict[str, Any] = Field(default_factory=dict)


class EffectDTO(BaseModel):
    """
    Шаблон эффекта в библиотеке (GameData).
    """

    effect_id: str
    name_en: str
    name_ru: str

    type: EffectType
    duration: int

    # --- 1. Ресурсы (DOT/HOT) ---
    # Базовое значение за ход.
    # Пример: {"hp": -10, "en": 5}
    resource_impact: dict[str, int] = Field(default_factory=dict)

    # --- 2. Статы (BUFF/DEBUFF) ---
    # Значения, которые добавляются в temp modifiers.
    # Пример: {"strength": 5.0, "armor": -10.0}
    raw_modifiers: dict[str, float] = Field(default_factory=dict)

    # --- 3. Логика (CONTROL) ---
    # Инструкции поведения.
    control_logic: ControlInstructionDTO | None = None

    # Теги (для диспела/иммунитета)
    tags: list[str] = Field(default_factory=list)

    description: str
