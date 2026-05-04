from pydantic import BaseModel, Field


class WorkerBatchJobDTO(BaseModel):
    """Аргументы для запуска Воркера через ARQ."""

    session_id: str
    batch_size: int


class AiTurnRequestDTO(BaseModel):
    """Задача для AI Worker."""

    session_id: str
    bot_id: int
    # Список целей, которые бот ОБЯЗАН атаковать (чтобы закрыть очередь)
    missing_targets: list[int] = Field(default_factory=list)


class CollectorSignalDTO(BaseModel):
    """Сигнал для триггера Колектора."""

    session_id: str
    char_id: int
    signal_type: str  # "check_immediate" | "check_timeout" | "heartbeat"
    move_id: str | None = None
