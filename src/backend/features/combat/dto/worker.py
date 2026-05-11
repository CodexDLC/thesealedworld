from pydantic import BaseModel, Field, field_validator

from src.backend.features.combat.dto.ids import ActorId, ActorIdLike, normalize_actor_id, normalize_actor_ids


class WorkerBatchJobDTO(BaseModel):
    """Аргументы для запуска Воркера через ARQ."""

    session_id: str
    batch_size: int


class AiTurnRequestDTO(BaseModel):
    """Задача для AI Worker."""

    session_id: str
    bot_id: ActorId
    # Список целей, которые бот ОБЯЗАН атаковать (чтобы закрыть очередь)
    missing_targets: list[ActorId] = Field(default_factory=list)

    @field_validator("bot_id", mode="before")
    @classmethod
    def _normalize_bot_id(cls, value: ActorIdLike) -> ActorId:
        return normalize_actor_id(value)

    @field_validator("missing_targets", mode="before")
    @classmethod
    def _normalize_missing_targets(cls, value: list[ActorIdLike]) -> list[ActorId]:
        return normalize_actor_ids(value)


class CollectorSignalDTO(BaseModel):
    """Сигнал для триггера Колектора."""

    session_id: str
    char_id: ActorId
    signal_type: str  # "check_immediate" | "check_timeout" | "heartbeat"
    move_id: str | None = None

    @field_validator("char_id", mode="before")
    @classmethod
    def _normalize_char_id(cls, value: ActorIdLike) -> ActorId:
        return normalize_actor_id(value)
