from typing import Literal

from pydantic import BaseModel, Field


class ContextRequestDTO(BaseModel):
    """
    Запрос на массовую сборку контекста.
    Принимает списки ID сущностей, для которых нужно подготовить снапшоты.
    """

    player_ids: list[int] = Field(default_factory=list)
    monster_ids: list[str] = Field(default_factory=list)  # UUID as strings
    pet_ids: list[int] = Field(default_factory=list)

    # Объем данных для сборки.
    # 'full' - всё (статы, инвентарь, скиллы).
    # 'combats' - только боевые статы, надетые вещи, боевые скиллы.
    # 'exploration' - статы для проверок в мире (восприятие, удача).
    # 'inventory' - полный инвентарь (сумка + экипировка) для UI.
    # 'status' - данные для экрана статуса.
    scope: Literal["full", "combats", "exploration", "inventory", "status"] = "full"


def _default_errors() -> dict[str, list[str | int]]:
    return {"player": [], "monster": [], "pet": []}


class ContextResponseDTO(BaseModel):
    """
    Результат сборки контекста.
    Содержит маппинг ID -> Redis Key для успешно обработанных сущностей
    и списки ID тех, кого не удалось найти.
    """

    # Успешные результаты: {entity_id: redis_key}
    player: dict[int, str] = Field(default_factory=dict)
    monster: dict[str, str] = Field(default_factory=dict)  # UUID as strings
    pet: dict[int, str] = Field(default_factory=dict)

    # Ошибки (не найдены или сбой): [entity_id]
    errors: dict[str, list[str | int]] = Field(default_factory=_default_errors)
