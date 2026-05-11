"""
DTO для действий (Actions) и намерений (Intents).
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from src.backend.features.combat.dto.ids import ActorId, ActorIdLike, normalize_actor_id, normalize_actor_ids
from src.backend.features.combat.dto.payloads import ExchangePayload, InstantPayload


class CombatMoveDTO(BaseModel):
    """
    Единица намерения (Intent).
    """

    move_id: str
    char_id: ActorId
    strategy: Literal["exchange", "item", "instant", "system"]

    # Полиморфный payload
    payload: ExchangePayload | InstantPayload | dict[str, Any] = Field(default_factory=dict)

    # Вспомогательные поля
    targets: list[ActorId] | None = None  # Резолвленные ID целей (заполняется сервером)

    @field_validator("char_id", mode="before")
    @classmethod
    def _normalize_char_id(cls, value: ActorIdLike) -> ActorId:
        return normalize_actor_id(value)

    @field_validator("targets", mode="before")
    @classmethod
    def _normalize_targets(cls, value: list[ActorIdLike] | None) -> list[ActorId] | None:
        return normalize_actor_ids(value) if value is not None else None


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
