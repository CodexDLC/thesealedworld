from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from src.backend.core.exceptions import BusinessLogicException
from src.backend.core.game_auth import require_internal_service_key
from src.backend.features.admin_players.dependencies import (
    get_admin_player_generation_service,
    get_admin_player_read_service,
)
from src.backend.features.admin_players.dto import (
    AdminPlayerCharacterDetailDTO,
    AdminPlayerCharacterListResponseDTO,
    AdminPlayerGenerateCharacterRequestDTO,
    AdminPlayerGenerateCharacterResponseDTO,
    AdminPlayerGenerationOptionsResponseDTO,
)

router = APIRouter(prefix="/api/admin/players", tags=["players-admin"])


@router.get("/users/{user_id}/characters", response_model=AdminPlayerCharacterListResponseDTO)
async def list_admin_user_characters(
    user_id: UUID,
    _service_key: object = Depends(require_internal_service_key),
    service=Depends(get_admin_player_read_service),
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AdminPlayerCharacterListResponseDTO:
    return await service.list_characters_for_user(user_id, limit=limit, offset=offset)


@router.get("/characters/{character_id}", response_model=AdminPlayerCharacterDetailDTO)
async def get_admin_character_detail(
    character_id: int,
    _service_key: object = Depends(require_internal_service_key),
    service=Depends(get_admin_player_read_service),
    inventory_limit: Annotated[int, Query(ge=1, le=100)] = 50,
    inventory_offset: Annotated[int, Query(ge=0)] = 0,
) -> AdminPlayerCharacterDetailDTO:
    detail = await service.get_character_detail(
        character_id,
        inventory_limit=inventory_limit,
        inventory_offset=inventory_offset,
    )
    if detail is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return detail


@router.get("/character-generation-options", response_model=AdminPlayerGenerationOptionsResponseDTO)
async def list_admin_character_generation_options(
    _service_key: object = Depends(require_internal_service_key),
    service=Depends(get_admin_player_generation_service),
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> AdminPlayerGenerationOptionsResponseDTO:
    return await service.list_generation_options(limit=limit)


@router.post("/users/{user_id}/characters/generate", response_model=AdminPlayerGenerateCharacterResponseDTO)
async def generate_admin_user_character(
    user_id: UUID,
    payload: AdminPlayerGenerateCharacterRequestDTO,
    _service_key: object = Depends(require_internal_service_key),
    service=Depends(get_admin_player_generation_service),
) -> AdminPlayerGenerateCharacterResponseDTO:
    try:
        return await service.generate_for_user(user_id, payload)
    except BusinessLogicException as exc:
        raise HTTPException(status_code=409, detail=exc.detail) from exc
