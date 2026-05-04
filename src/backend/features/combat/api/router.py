from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.backend.features.combat.dependencies import CombatRuntimeOrchestratorDep  # noqa: TC001
from src.backend.features.combat.services.session_service import CombatSessionNotFound
from src.shared.enums import CoreDomain
from src.shared.schemas.combat import (
    CombatDashboardDTO,
    CombatLogDTO,
    CombatRegisterMoveRequestDTO,  # noqa: TC001 - FastAPI needs the body model at runtime
)
from src.shared.schemas.response import CoreResponseDTO, GameStateHeader

router = APIRouter(prefix="/api/game/combat", tags=["combat"])


# TODO(combat-api): These endpoints are transitional browser API stubs. Keep
# shared schemas as the public contract: runtime orchestrator builds payload DTOs,
# route handlers only choose whether the response needs CoreResponseDTO envelope.
# TODO(combat-api): Define combat-specific error response variants before
# finalizing the browser contract, instead of leaking raw ValueError/HTTP detail.
@router.get("/{char_id}/view", response_model=CoreResponseDTO[CombatDashboardDTO])
async def get_combat_view(
    char_id: int, orchestrator: CombatRuntimeOrchestratorDep
) -> CoreResponseDTO[CombatDashboardDTO]:
    try:
        payload = await orchestrator.get_initial_view(char_id)
        return CoreResponseDTO(
            header=GameStateHeader(current_state=CoreDomain.COMBAT),
            payload=payload,
            payload_type="CombatDashboard",
        )
    except CombatSessionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{char_id}/snapshot", response_model=CombatDashboardDTO)
async def get_combat_snapshot(char_id: int, orchestrator: CombatRuntimeOrchestratorDep) -> CombatDashboardDTO:
    try:
        return await orchestrator.get_dashboard(char_id)
    except CombatSessionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{char_id}/logs", response_model=CombatLogDTO)
async def get_combat_logs(
    char_id: int,
    orchestrator: CombatRuntimeOrchestratorDep,
    page: int = 1,
    page_size: int = 20,
) -> CombatLogDTO:
    try:
        return await orchestrator.get_logs(char_id, page=page, page_size=page_size)
    except CombatSessionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{char_id}/moves", response_model=CombatDashboardDTO)
async def register_combat_move(
    char_id: int,
    body: CombatRegisterMoveRequestDTO,
    orchestrator: CombatRuntimeOrchestratorDep,
) -> CombatDashboardDTO:
    try:
        return await orchestrator.register_move(char_id, body)
    except CombatSessionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
