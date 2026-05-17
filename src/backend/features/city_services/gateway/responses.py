from __future__ import annotations

from typing import Any

from src.shared.enums import CoreDomain
from src.shared.schemas import CoreResponseDTO, GameStateHeader, StateTransitionDTO


def city_service_response(payload: Any) -> CoreResponseDTO[Any]:
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.CITY_SERVICES),
        payload=payload,
        payload_type="city_service_screen",
    )


def city_service_error(message: str) -> CoreResponseDTO[Any]:
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.CITY_SERVICES, error=message),
        payload=None,
        payload_type="city_service_error",
    )


def city_service_transition(transition: StateTransitionDTO) -> CoreResponseDTO[Any]:
    return CoreResponseDTO(
        header=GameStateHeader(current_state=transition.target_state, previous_state=CoreDomain.CITY_SERVICES),
        payload=transition,
        payload_type="state_transition",
    )
