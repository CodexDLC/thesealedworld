from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from src.shared.enums.domain_enums import CoreDomain

T = TypeVar("T")
M = TypeVar("M")


class ServiceResult(BaseModel):
    """
    Wrapper для возврата из Service в Gateway.
    Используется когда нужно передать next_state для смены FSM.
    """

    data: Any
    next_state: CoreDomain | None = None


class GameStateHeader(BaseModel):
    """
    Мета-информация для навигации Бота.
    """

    current_state: CoreDomain = Field(..., description="Куда переключить UI бота")
    previous_state: CoreDomain | None = None
    transaction_id: str = Field(default_factory=str, description="Trace ID для логов")

    # Опционально: можно добавить error_code сюда, если header отвечает за статус
    error: str | None = None


class CoreResponseDTO(BaseModel, Generic[T]):
    """
    Базовый транспортный конверт.
    Наследовать его не обязательно, достаточно использовать Generic[T].
    """

    header: GameStateHeader
    payload: T | None = None
    payload_type: str | None = None  # Тип пейлоада (encounter, list, navigation)


class CoreCompositeResponseDTO(BaseModel, Generic[T, M]):
    """
    Расширенный транспортный конверт для двухпанельного UI.
    Содержит данные для основного контента (payload) и для меню (menu_payload).
    """

    header: GameStateHeader
    payload: T | None = None
    menu_payload: M | None = None
    payload_type: str | None = None
