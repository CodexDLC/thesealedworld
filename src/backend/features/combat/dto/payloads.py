from pydantic import BaseModel, field_validator

from src.backend.features.combat.dto.ids import ActorId, ActorIdLike, normalize_actor_id, normalize_actor_ids


class ExchangePayload(BaseModel):
    """Данные для стратегии 'exchange' (Combat)."""

    target_id: ActorId  # В обмене всегда одна конкретная цель из очереди.

    @field_validator("target_id", mode="before")
    @classmethod
    def _normalize_target_id(cls, value: ActorIdLike) -> ActorId:
        return normalize_actor_id(value)

    # Финт (опционально)
    feint_id: str | None = None


class InstantPayload(BaseModel):
    """Данные для стратегии 'instant' (Abilities / Items)."""

    # В инстанте может быть ID, список ID или инструкция (TargetType)
    target_id: ActorId | list[ActorId] | None = None

    ability_id: str | None = None  # ID способности
    item_id: int | str | None = None  # ID предмета или combat item action id (если это расходник)
    feint_id: str | None = None  # ID финта (если это мгновенный финт, например "песок в глаза")

    @field_validator("target_id", mode="before")
    @classmethod
    def _normalize_target_id(cls, value: ActorIdLike | list[ActorIdLike] | None) -> ActorId | list[ActorId] | None:
        if value is None:
            return None
        if isinstance(value, list):
            return normalize_actor_ids(value)
        return normalize_actor_id(value)
