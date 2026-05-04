"""
DTO для действий (Actions) и намерений (Intents).
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.backend.domains.user_features.combat.dto.payloads import ExchangePayload, InstantPayload


class CombatMoveDTO(BaseModel):
    """
    Единица намерения (Intent).
    """

    move_id: str
    char_id: int | str
    strategy: Literal["exchange", "item", "instant", "system"]

    # Полиморфный payload
    payload: ExchangePayload | InstantPayload | dict[str, Any] = Field(default_factory=dict)

    # Вспомогательные поля
    targets: list[int] | None = None  # Резолвленные ID целей (заполняется сервером)


class CombatActionDTO(BaseModel):
    """
    Пара действий (Action Pair).
    """

    action_type: Literal["exchange", "item", "instant", "system"]
    move: CombatMoveDTO
    partner_move: CombatMoveDTO | None = None  # Ответный удар (только для exchange)

    is_forced: bool = False  # Если true, то partner_move не обязателен (безответный удар)


class CombatActionResultDTO(BaseModel):
    """
    Результат выполнения действия (для API/Клиента).
    """

    success: bool = True
    error: str | None = None
    events: list[dict[str, Any]] = Field(default_factory=list)
