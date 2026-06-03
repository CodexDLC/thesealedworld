from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from loguru import logger

from src.backend.features.combat.dependencies import CombatRuntimeOrchestratorDep  # noqa: TC001
from src.backend.features.combat.exceptions import CombatActionRejectedError, CombatAPIError, CombatError
from src.backend.features.combat.services.session_service import CombatSessionNotFound
from src.shared.enums import CoreDomain
from src.shared.schemas.combat import (
    CombatDashboardDTO,
    CombatErrorResponseDTO,
    CombatLogDTO,
    CombatPinFeintRequestDTO,  # noqa: TC001 - FastAPI needs the body model at runtime
    CombatRegisterMoveRequestDTO,  # noqa: TC001 - FastAPI needs the body model at runtime
    CombatResultDTO,
)
from src.shared.schemas.response import CoreResponseDTO, GameStateHeader, StateTransitionDTO

COMBAT_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": CombatErrorResponseDTO},
    404: {"model": CombatErrorResponseDTO},
}

router = APIRouter(prefix="/api/game/combat", tags=["combat"], responses=COMBAT_ERROR_RESPONSES)


# TODO(combat-api): These endpoints are transitional browser API stubs. Keep
# shared schemas as the public contract: runtime orchestrator builds payload DTOs,
# route handlers only choose whether the response needs CoreResponseDTO envelope.
@router.get(
    "/{char_id}/view", response_model=CoreResponseDTO[CombatDashboardDTO | CombatResultDTO | StateTransitionDTO]
)
async def get_combat_view(
    char_id: int, orchestrator: CombatRuntimeOrchestratorDep
) -> CoreResponseDTO[CombatDashboardDTO | CombatResultDTO | StateTransitionDTO]:
    """Return the public combat surface for a character entry into combat UI."""
    try:
        payload: CombatDashboardDTO | CombatResultDTO = await orchestrator.get_initial_view(char_id)
        current_state = CoreDomain.COMBAT_RESULT if isinstance(payload, CombatResultDTO) else CoreDomain.COMBAT
        return CoreResponseDTO(
            header=GameStateHeader(current_state=current_state),
            payload=payload,
            payload_type="CombatResult" if isinstance(payload, CombatResultDTO) else "CombatDashboard",
        )
    except CombatSessionNotFound as exc:
        archived = await orchestrator.find_archived_result(char_id, reason=str(exc))
        if archived is None:
            transition = await orchestrator.recover_missing_combat_transition(char_id, reason=str(exc))
            return CoreResponseDTO(
                header=GameStateHeader(current_state=transition.target_state, error="combat_session_recovered"),
                payload=transition,
                payload_type="state_transition",
            )
        return CoreResponseDTO(
            header=GameStateHeader(current_state=CoreDomain.COMBAT_RESULT, error="combat_result_recovered"),
            payload=archived,
            payload_type="CombatResult",
        )


@router.get("/{char_id}/snapshot", response_model=CombatDashboardDTO)
async def get_combat_snapshot(char_id: int, orchestrator: CombatRuntimeOrchestratorDep) -> CombatDashboardDTO:
    """Return the current live combat dashboard without CoreResponse wrapping."""
    try:
        return await orchestrator.get_dashboard(char_id)
    except CombatError as exc:
        raise CombatAPIError(exc, context={"char_id": char_id}) from exc


@router.get("/{char_id}/logs", response_model=CombatLogDTO)
async def get_combat_logs(
    char_id: int,
    orchestrator: CombatRuntimeOrchestratorDep,
    page: int = 1,
    page_size: int = 20,
) -> CombatLogDTO:
    """Return paginated combat logs from the live or archived combat source."""
    try:
        return await orchestrator.get_logs(char_id, page=page, page_size=page_size)
    except CombatError as exc:
        raise CombatAPIError(exc, context={"char_id": char_id}) from exc


@router.post("/{char_id}/moves", response_model=CombatDashboardDTO | CombatResultDTO)
async def register_combat_move(
    char_id: int,
    body: CombatRegisterMoveRequestDTO,
    orchestrator: CombatRuntimeOrchestratorDep,
) -> CombatDashboardDTO | CombatResultDTO:
    """Accept one combat move request and return the updated runtime surface."""
    try:
        logger.bind(char_id=char_id, action=body.action).info("CombatMoveAccepted")
        return await orchestrator.register_move(char_id, body)
    except CombatError as exc:
        logger.bind(char_id=char_id, code=exc.code, detail=exc.message).warning("CombatMoveRejected")
        raise CombatAPIError(exc, context={"char_id": char_id}) from exc
    except ValueError as exc:
        logger.bind(char_id=char_id, detail=str(exc)).warning("CombatMoveRejected")
        raise CombatAPIError(
            CombatActionRejectedError("Combat action rejected", context={"reason": str(exc)}),
            context={"char_id": char_id},
        ) from exc


@router.post("/{char_id}/feints/pin", response_model=CombatDashboardDTO)
async def pin_combat_feint(
    char_id: int,
    body: CombatPinFeintRequestDTO,
    orchestrator: CombatRuntimeOrchestratorDep,
) -> CombatDashboardDTO:
    """Pin or unpin one feint in the player's live combat hand."""
    try:
        return await orchestrator.pin_feint(char_id, body)
    except CombatError as exc:
        logger.bind(char_id=char_id, code=exc.code, detail=exc.message).warning("CombatFeintPinRejected")
        raise CombatAPIError(exc, context={"char_id": char_id}) from exc
    except ValueError as exc:
        logger.bind(char_id=char_id, detail=str(exc)).warning("CombatFeintPinRejected")
        raise CombatAPIError(
            CombatActionRejectedError("Combat feint pin rejected", context={"reason": str(exc)}),
            context={"char_id": char_id},
        ) from exc


@router.post("/{char_id}/result/continue", response_model=CoreResponseDTO[StateTransitionDTO])
async def continue_combat_result(
    char_id: int,
    orchestrator: CombatRuntimeOrchestratorDep,
) -> CoreResponseDTO[StateTransitionDTO]:
    """Advance the player out of post-combat result state into the next state."""
    transition = await orchestrator.continue_result(char_id)
    return CoreResponseDTO(
        header=GameStateHeader(current_state=transition.target_state),
        payload=transition,
        payload_type="state_transition",
    )
