from typing import Annotated

from fastapi import APIRouter, Body, Path, Query

from src.backend.dependencies.features.inventory import InventoryGatewayDep
from src.shared.schemas.inventory import InventoryUIPayloadDTO
from src.shared.schemas.response import CoreResponseDTO

router = APIRouter(prefix="/inventory", tags=["Inventory"])


# --- Views (GET) ---


@router.get("/{char_id}/main", response_model=CoreResponseDTO[InventoryUIPayloadDTO])
async def get_main_menu(
    gateway: InventoryGatewayDep,
    char_id: int = Path(..., description="ID персонажа"),
) -> CoreResponseDTO[InventoryUIPayloadDTO]:
    """
    Получение главного экрана инвентаря (Кукла).
    """
    return await gateway.get_view(char_id, "main")


@router.get("/{char_id}/bag", response_model=CoreResponseDTO[InventoryUIPayloadDTO])
async def get_bag_view(
    gateway: InventoryGatewayDep,
    char_id: int = Path(..., description="ID персонажа"),
    section: str = Query("all", description="Раздел (equip, resource, consumable)"),
    category: str | None = Query(None, description="Подкатегория"),
    page: int = Query(0, description="Номер страницы"),
) -> CoreResponseDTO[InventoryUIPayloadDTO]:
    """
    Получение содержимого сумки.
    """
    return await gateway.get_view(char_id, "bag", section=section, category=category, page=page)


@router.get("/{char_id}/items/{item_id}", response_model=CoreResponseDTO[InventoryUIPayloadDTO])
async def get_item_details(
    gateway: InventoryGatewayDep,
    char_id: int = Path(..., description="ID персонажа"),
    item_id: int = Path(..., description="ID предмета"),
) -> CoreResponseDTO[InventoryUIPayloadDTO]:
    """
    Получение деталей предмета.
    """
    return await gateway.get_view(char_id, "details", item_id=item_id)


# --- Actions (POST) ---


@router.post("/{char_id}/items/{item_id}/equip", response_model=CoreResponseDTO[InventoryUIPayloadDTO])
async def equip_item(
    gateway: InventoryGatewayDep,
    char_id: int = Path(..., description="ID персонажа"),
    item_id: int = Path(..., description="ID предмета"),
    slot: Annotated[str | None, Body(embed=True)] = None,
) -> CoreResponseDTO[InventoryUIPayloadDTO]:
    """
    Надеть предмет.
    """
    return await gateway.handle_action(char_id, "equip", item_id=item_id, slot=slot)


@router.post("/{char_id}/items/{item_id}/unequip", response_model=CoreResponseDTO[InventoryUIPayloadDTO])
async def unequip_item(
    gateway: InventoryGatewayDep,
    char_id: int = Path(..., description="ID персонажа"),
    item_id: int = Path(..., description="ID предмета"),
) -> CoreResponseDTO[InventoryUIPayloadDTO]:
    """
    Снять предмет.
    """
    return await gateway.handle_action(char_id, "unequip", item_id=item_id)


# --- Destruction (DELETE) ---


@router.delete("/{char_id}/items/{item_id}", response_model=CoreResponseDTO[InventoryUIPayloadDTO])
async def drop_item(
    gateway: InventoryGatewayDep,
    char_id: int = Path(..., description="ID персонажа"),
    item_id: int = Path(..., description="ID предмета"),
) -> CoreResponseDTO[InventoryUIPayloadDTO]:
    """
    Выбросить предмет.
    """
    return await gateway.handle_delete(char_id, item_id)
