"""
Модуль содержит DTO (Data Transfer Objects) для работы с персонажами.

Определяет структуры данных для создания "оболочки" персонажа,
обновления данных после онбординга, чтения полной информации о персонаже,
а также для обновления и чтения его атрибутов (ранее stats).
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

Gender = Literal["male", "female", "other"]  # Возможные значения для пола персонажа.


class CharacterShellCreateDTO(BaseModel):
    """
    DTO для создания "оболочки" персонажа.
    Содержит только идентификатор пользователя Telegram, который создает персонажа.
    """

    user_id: int  # Уникальный идентификатор пользователя Telegram.


class CharacterShellDTO(BaseModel):
    """
    DTO для возврата ID созданной оболочки.
    """

    character_id: int


class CharacterOnboardingUpdateDTO(BaseModel):
    """
    DTO для обновления данных персонажа после прохождения онбординга.
    Используется для сохранения имени, пола и текущей стадии игры.
    """

    name: str  # Имя персонажа, выбранное игроком.
    gender: Gender  # Пол персонажа ("male", "female", "other").
    game_stage: str  # Текущая стадия игры персонажа (например, "creation", "in_game").


class CharacterReadDTO(BaseModel):
    """
    DTO для чтения полной информации о персонаже из базы данных.
    Включает все основные атрибуты персонажа.
    """

    character_id: int  # Уникальный идентификатор персонажа в игре.
    user_id: int  # Идентификатор пользователя Telegram, которому принадлежит персонаж.
    name: str  # Имя персонажа.
    gender: Gender  # Пол персонажа.
    game_stage: str  # Текущая стадия игры персонажа.

    # Расширенные поля для контекста и навигации
    prev_game_stage: str | None = None
    location_id: str = "52_52"
    prev_location_id: str | None = None

    # Snapshots (JSONB)
    vitals_snapshot: dict[str, Any] | None = None
    active_sessions: dict[str, Any] | None = None

    created_at: datetime  # Дата и время создания персонажа.
    updated_at: datetime  # Дата и время последнего обновления данных персонажа.

    model_config = ConfigDict(from_attributes=True)


class CharacterAttributesUpdateDTO(BaseModel):
    """
    DTO для обновления атрибутов персонажа (ранее Stats).
    Используется для изменения базовых характеристик.
    """

    strength: int  # Сила: влияет на физический урон, переносимый вес.
    agility: int  # Ловкость: влияет на уклонение, точность, скорость атаки.
    endurance: int  # Выносливость: влияет на максимальное HP, физическое сопротивление.
    intelligence: int  # Интеллект: влияет на магический урон, эффективность заклинаний.
    wisdom: int  # Мудрость: влияет на магическое сопротивление, шанс крита заклинаний.
    men: int  # Дух: влияет на максимальную энергию/ману, сопротивление контролю.
    perception: int  # Восприятие: влияет на шанс найти лут, обнаружение ловушек, слоты инвентаря.
    charisma: int  # Харизма: влияет на цены у торговцев, эффективность питомцев, социальные навыки.
    luck: int  # Удача: влияет на шанс крита, шанс найти лут, успех крафта.


class CharacterAttributesReadDTO(CharacterAttributesUpdateDTO):
    """
    DTO для чтения атрибутов персонажа из базы данных.
    Включает поля из `CharacterAttributesUpdateDTO` и временные метки.
    """

    created_at: datetime | None = None  # Дата и время создания записи атрибутов.
    updated_at: datetime | None = None  # Дата и время последнего обновления записи атрибутов.
    character_id: int = 0  # Added default value for dummy creation

    model_config = ConfigDict(from_attributes=True)


# Aliases for backward compatibility during refactoring (Optional, but safer)
CharacterStatsUpdateDTO = CharacterAttributesUpdateDTO
CharacterStatsReadDTO = CharacterAttributesReadDTO
