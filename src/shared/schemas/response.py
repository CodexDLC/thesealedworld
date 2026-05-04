import uuid
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from src.shared.enums.domain import CoreDomain

T_co = TypeVar("T_co", covariant=True)
M_co = TypeVar("M_co", covariant=True)


class StateTransitionDTO(BaseModel):
    char_id: int
    target_state: CoreDomain
    reason: str
    quest_key: str | None = None
    combat_id: str | None = None
    arena_id: str | None = None
    location_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GameStateHeader(BaseModel):
    current_state: CoreDomain = Field(..., description="Current game UI/domain state.")
    previous_state: CoreDomain | None = None
    transaction_id: str = Field(
        default_factory=lambda: uuid.uuid4().hex, description="Trace ID for logs and UI correlation."
    )
    error: str | None = None


class CoreResponseDTO(BaseModel, Generic[T_co]):  # noqa: UP046
    header: GameStateHeader
    payload: T_co | None = None
    payload_type: str | None = None


class CoreCompositeResponseDTO(BaseModel, Generic[T_co, M_co]):  # noqa: UP046
    header: GameStateHeader
    payload: T_co | None = None
    menu_payload: M_co | None = None


class ServiceResult(BaseModel):
    data: Any
    next_state: CoreDomain | None = None
    header_update: dict[str, Any] | None = None
