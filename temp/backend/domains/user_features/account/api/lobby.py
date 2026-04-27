from fastapi import APIRouter, Depends

from src.backend.dependencies.features.account import get_lobby_gateway, get_login_gateway
from src.backend.domains.user_features.account.gateway.lobby_gateway import LobbyGateway
from src.backend.domains.user_features.account.gateway.login_gateway import LoginGateway
from src.shared.schemas.response import CoreResponseDTO

router = APIRouter(tags=["Account Lobby"])

# --- Lobby Actions ---


@router.post("/{user_id}/initialize", response_model=CoreResponseDTO)
async def initialize_lobby(user_id: int, gateway: LobbyGateway = Depends(get_lobby_gateway)):
    """
    Вход в лобби. Если персонажей нет - создает первого.
    """
    return await gateway.initialize(user_id)


@router.get("/{user_id}/characters", response_model=CoreResponseDTO)
async def list_characters(user_id: int, gateway: LobbyGateway = Depends(get_lobby_gateway)):
    return await gateway.list_characters(user_id)


@router.post("/{user_id}/characters", response_model=CoreResponseDTO)
async def create_character(user_id: int, gateway: LobbyGateway = Depends(get_lobby_gateway)):
    """
    Явное создание персонажа.
    """
    return await gateway.create_character(user_id)


@router.delete("/characters/{char_id}", response_model=CoreResponseDTO)
async def delete_character(char_id: int, user_id: int, gateway: LobbyGateway = Depends(get_lobby_gateway)):
    return await gateway.delete_character(char_id, user_id)


# --- Login Actions ---


@router.post("/{user_id}/characters/{char_id}/login", response_model=CoreResponseDTO)
async def login_character(user_id: int, char_id: int, gateway: LoginGateway = Depends(get_login_gateway)):
    """
    Вход в игру выбранным персонажем.
    """
    return await gateway.login(char_id, user_id)
