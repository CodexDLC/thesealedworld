import uuid

from pydantic import BaseModel, Field

from src.shared.enums.domain import CoreDomain


class GameStateHeader(BaseModel):
    current_state: CoreDomain = Field(..., description="Current game UI/domain state.")
    previous_state: CoreDomain | None = None
    transaction_id: str = Field(
        default_factory=lambda: uuid.uuid4().hex, description="Trace ID for logs and UI correlation."
    )
    error: str | None = None


class CoreResponseDTO[T](BaseModel):
    header: GameStateHeader
    payload: T | None = None
    payload_type: str | None = None


class CoreCompositeResponseDTO[T, M](BaseModel):
    header: GameStateHeader
    payload: T | None = None
    menu_payload: M | None = None
    payload_type: str | None = None
