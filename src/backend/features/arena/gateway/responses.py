from __future__ import annotations

from typing import Any

from src.shared.enums import CoreDomain
from src.shared.schemas.arena import ArenaScreenEnum, ArenaUIPayloadDTO
from src.shared.schemas.response import CoreResponseDTO, GameStateHeader, StateTransitionDTO


def arena_response(payload: ArenaUIPayloadDTO) -> CoreResponseDTO[Any]:
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.ARENA),
        payload=payload,
        payload_type="arena_screen",
    )


def arena_error(message: str) -> CoreResponseDTO[Any]:
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.ARENA, error=message),
        payload=ArenaUIPayloadDTO(
            screen=ArenaScreenEnum.MATCH_FOUND,
            title="Ошибка арены",
            description=message,
            buttons=[],
        ),
        payload_type="arena_error",
    )


def combat_transition(char_id: int, payload: ArenaUIPayloadDTO, *, reason: str) -> CoreResponseDTO[Any]:
    transition = StateTransitionDTO(
        char_id=char_id,
        target_state=CoreDomain.COMBAT,
        reason=reason,
        combat_id=payload.combat_id,
        arena_id=payload.arena_session_id,
        metadata=payload.model_dump(mode="json"),
    )
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.COMBAT, previous_state=CoreDomain.ARENA),
        payload=transition,
        payload_type="state_transition",
    )


def exploration_transition(char_id: int, *, reason: str) -> CoreResponseDTO[Any]:
    transition = StateTransitionDTO(char_id=char_id, target_state=CoreDomain.EXPLORATION, reason=reason)
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.EXPLORATION, previous_state=CoreDomain.ARENA),
        payload=transition,
        payload_type="state_transition",
    )
