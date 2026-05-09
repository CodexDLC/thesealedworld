from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.backend.features.character.repositories import CharacterRepository
from src.backend.features.inventory.dependencies import get_character_repository, get_inventory_service
from src.backend.features.inventory.services.inventory_service import (
    InventoryActionError,
    InventoryActionForbiddenError,
    InventoryService,
)
from src.backend.features_site.auth.dependencies import get_current_user
from src.backend.features_site.auth.models import User
from src.shared.enums import CoreDomain
from src.shared.schemas.inventory import (
    InventoryActionRequestDTO,
    InventoryCloseRequestDTO,
    InventoryWindowDTO,
)
from src.shared.schemas.response import CoreResponseDTO, GameStateHeader

router = APIRouter(prefix="/api/game/inventory", tags=["inventory"])


@router.get("/{char_id}/view", response_model=CoreResponseDTO[InventoryWindowDTO])
async def get_inventory_view(
    char_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
    characters: Annotated[CharacterRepository, Depends(get_character_repository)],
) -> CoreResponseDTO[InventoryWindowDTO]:
    await _ensure_owner(characters, current_user, char_id)
    payload = await service.open_window(char_id)
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.INVENTORY), payload=payload, payload_type="inventory"
    )


@router.post("/actions", response_model=CoreResponseDTO[InventoryWindowDTO])
async def apply_inventory_action(
    dto: InventoryActionRequestDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
    characters: Annotated[CharacterRepository, Depends(get_character_repository)],
) -> CoreResponseDTO[InventoryWindowDTO]:
    await _ensure_owner(characters, current_user, dto.char_id)
    try:
        payload = await service.apply_action(dto)
    except InventoryActionForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.payload.model_dump(mode="json")) from exc
    except InventoryActionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.INVENTORY), payload=payload, payload_type="inventory"
    )


@router.post("/close", response_model=CoreResponseDTO[InventoryWindowDTO])
async def close_inventory(
    dto: InventoryCloseRequestDTO,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
    characters: Annotated[CharacterRepository, Depends(get_character_repository)],
) -> CoreResponseDTO[InventoryWindowDTO]:
    await _ensure_owner(characters, current_user, dto.char_id)
    payload = await service.close_window(dto.char_id)
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.INVENTORY), payload=payload, payload_type="inventory"
    )


async def _ensure_owner(characters: CharacterRepository, user: User, char_id: int) -> None:
    character = await characters.get_by_id_and_user_id(char_id, user.id)
    if character is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")
