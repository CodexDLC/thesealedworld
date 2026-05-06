"""
Модуль содержит DTO (Data Transfer Objects) для работы с персонажами.

Определяет структуры данных для создания "оболочки" персонажа,
обновления данных после онбординга, чтения полной информации о персонаже,
а также для обновления и чтения его атрибутов (ранее stats).
"""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    user_id: uuid.UUID | int  # Идентификатор пользователя, которому принадлежит персонаж.
    name: str  # Имя персонажа.
    gender: Gender  # Пол персонажа.
    avatar_url: str | None = None
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


class CharacterStatusDTO(BaseModel):
    character_id: int
    name: str
    avatar_url: str | None = None
    hp: float = 0
    max_hp: float = 0
    energy: float = 0
    max_energy: float = 0
    stamina: float = 0
    max_stamina: float = 0
    last_update: datetime | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


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
    intellect: int = 8
    memory: int = 8
    mental: int = 8
    projection: int = 8
    prediction: int = 8

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _normalize_attribute_names(cls, data: Any) -> Any:
        if data is None:
            return data

        keys = {
            "character_id",
            "strength",
            "agility",
            "endurance",
            "perception",
            "intelligence",
            "wisdom",
            "men",
            "charisma",
            "luck",
            "intellect",
            "memory",
            "mental",
            "projection",
            "prediction",
            "created_at",
            "updated_at",
        }
        payload = (
            dict(data) if isinstance(data, dict) else {key: getattr(data, key) for key in keys if hasattr(data, key)}
        )
        aliases = {
            "intelligence": "intellect",
            "wisdom": "memory",
            "men": "mental",
            "charisma": "projection",
            "luck": "prediction",
        }
        for legacy_key, current_key in aliases.items():
            if current_key not in payload and legacy_key in payload:
                payload[current_key] = payload[legacy_key]
            if legacy_key not in payload and current_key in payload:
                payload[legacy_key] = payload[current_key]
        return payload


# Aliases for backward compatibility during refactoring (Optional, but safer)
CharacterStatsUpdateDTO = CharacterAttributesUpdateDTO
CharacterStatsReadDTO = CharacterAttributesReadDTO
