from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from src.backend.config.settings import settings
from src.backend.features.rift.dependencies import (
    get_rift_dev_service,
    get_rift_game_player_service,
    get_rift_player_service,
)
from src.backend.features.rift.dto import (
    RiftActionRequestDTO,
    RiftActionResponseDTO,
    RiftExitResponseDTO,
    RiftRebuildRequestDTO,
    RiftScreenDTO,
    RiftStartRequestDTO,
    RiftTravelStartRequestDTO,
    RiftTravelTickRequestDTO,
    RiftTravelTickResponseDTO,
)
from src.backend.features.rift.integrations import RiftRuntimeNotFoundError
from src.backend.features.rift.services import RiftDevService, RiftPlayerService  # noqa: TC001

dev_router = APIRouter(prefix="/api/dev/rift", tags=["rift-dev"])
game_router = APIRouter(prefix="/api/game/rift", tags=["rift"])


@game_router.get("/{char_id}/view", response_model=RiftScreenDTO)
async def get_player_rift_screen(
    char_id: int,
    service: Annotated[RiftPlayerService, Depends(get_rift_player_service)],
) -> RiftScreenDTO:
    try:
        return await service.screen(char_id)
    except (RiftRuntimeNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@game_router.post("/{char_id}/leave", response_model=RiftExitResponseDTO)
async def leave_player_rift(
    char_id: int,
    service: Annotated[RiftPlayerService, Depends(get_rift_player_service)],
) -> RiftExitResponseDTO:
    try:
        return await service.leave(char_id)
    except (RiftRuntimeNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@game_router.post("/{char_id}/travel/start", response_model=RiftTravelTickResponseDTO)
async def start_player_rift_travel(
    char_id: int,
    request: RiftTravelStartRequestDTO,
    service: Annotated[RiftPlayerService, Depends(get_rift_game_player_service)],
) -> RiftTravelTickResponseDTO:
    try:
        return await service.start_travel(char_id, request)
    except (RiftRuntimeNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@game_router.post("/{char_id}/travel/tick", response_model=RiftTravelTickResponseDTO)
async def tick_player_rift_travel(
    char_id: int,
    request: RiftTravelTickRequestDTO,
    service: Annotated[RiftPlayerService, Depends(get_rift_game_player_service)],
) -> RiftTravelTickResponseDTO:
    try:
        return await service.tick_travel(char_id, request)
    except (RiftRuntimeNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@game_router.post("/{char_id}/action", response_model=RiftActionResponseDTO)
async def run_player_rift_action(
    char_id: int,
    request: RiftActionRequestDTO,
    service: Annotated[RiftPlayerService, Depends(get_rift_game_player_service)],
) -> RiftActionResponseDTO:
    try:
        return await service.run_action(char_id, request)
    except (RiftRuntimeNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@game_router.post("/{char_id}/complete", response_model=RiftExitResponseDTO)
async def complete_player_rift(
    char_id: int,
    service: Annotated[RiftPlayerService, Depends(get_rift_player_service)],
) -> RiftExitResponseDTO:
    try:
        return await service.complete(char_id)
    except (RiftRuntimeNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@dev_router.post("/starter-rift/start", response_model=RiftScreenDTO)
async def start_starter_rift(
    request: RiftStartRequestDTO,
    service: Annotated[RiftDevService, Depends(get_rift_dev_service)],
) -> RiftScreenDTO:
    return await service.start(request)


@dev_router.get("/{rift_instance_id}/screen", response_model=RiftScreenDTO)
async def get_rift_screen(
    rift_instance_id: str,
    service: Annotated[RiftDevService, Depends(get_rift_dev_service)],
) -> RiftScreenDTO:
    try:
        return await service.screen(rift_instance_id)
    except RiftRuntimeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@dev_router.post("/{rift_instance_id}/travel/start", response_model=RiftTravelTickResponseDTO)
async def start_rift_travel(
    rift_instance_id: str,
    request: RiftTravelStartRequestDTO,
    service: Annotated[RiftDevService, Depends(get_rift_dev_service)],
) -> RiftTravelTickResponseDTO:
    try:
        return await service.start_travel(rift_instance_id, request)
    except RiftRuntimeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@dev_router.post("/{rift_instance_id}/travel/tick", response_model=RiftTravelTickResponseDTO)
async def tick_rift_travel(
    rift_instance_id: str,
    request: RiftTravelTickRequestDTO,
    service: Annotated[RiftDevService, Depends(get_rift_dev_service)],
) -> RiftTravelTickResponseDTO:
    try:
        return await service.tick_travel(rift_instance_id, request)
    except RiftRuntimeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@dev_router.post("/{rift_instance_id}/action", response_model=RiftActionResponseDTO)
async def run_rift_action(
    rift_instance_id: str,
    request: RiftActionRequestDTO,
    service: Annotated[RiftDevService, Depends(get_rift_dev_service)],
) -> RiftActionResponseDTO:
    try:
        return await service.run_action(rift_instance_id, request)
    except RiftRuntimeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@dev_router.post("/{rift_instance_id}/rebuild", response_model=RiftScreenDTO)
async def rebuild_rift(
    rift_instance_id: str,
    request: RiftRebuildRequestDTO,
    service: Annotated[RiftDevService, Depends(get_rift_dev_service)],
) -> RiftScreenDTO:
    try:
        return await service.rebuild(
            rift_instance_id,
            seed=request.seed,
            scale_preset_key=request.scale_preset_key,
            assembly_preset_key=request.assembly_preset_key,
            void_cells=request.void_cells,
        )
    except RiftRuntimeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def build_rift_router(*, enable_dev_routes: bool = True) -> APIRouter:
    api_router = APIRouter()
    api_router.include_router(game_router)
    if enable_dev_routes:
        api_router.include_router(dev_router)
    return api_router


router = build_rift_router(enable_dev_routes=settings.enable_dev_rift_routes)
