from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.shared.enums import CoreDomain
from src.shared.schemas import CoreResponseDTO, GameStateHeader, StateTransitionDTO

if TYPE_CHECKING:
    from src.shared.schemas.tavern import TavernUIPayloadDTO


def tavern_response(payload: TavernUIPayloadDTO) -> CoreResponseDTO[Any]:
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.TAVERN),
        payload=payload,
        payload_type="tavern_screen",
    )


def tavern_error(message: str) -> CoreResponseDTO[Any]:
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.TAVERN, error=message),
        payload=None,
        payload_type="tavern_error",
    )


def tavern_transition(transition: StateTransitionDTO) -> CoreResponseDTO[Any]:
    return CoreResponseDTO(
        header=GameStateHeader(current_state=transition.target_state, previous_state=CoreDomain.TAVERN),
        payload=transition,
        payload_type="state_transition",
    )
