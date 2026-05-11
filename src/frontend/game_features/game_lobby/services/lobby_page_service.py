from fastapi import Request
from loguru import logger

from src.frontend.integrations.backend_api.game_lobby import (
    BackendGameLobbyApi,
    GameLobbyEnterResponse,
    GameLobbyReleaseResponse,
    GameLobbyResponse,
    GameLobbyStartResponse,
)
from src.frontend.site_features.auth.token_state import require_access_token
from src.shared.schemas import (
    CharacterStatusDTO,
    CreateCharacterRequestDTO,
    DeleteCharacterRequestDTO,
    EnterCharacterRequestDTO,
)


class GameLobbyPageService:
    def __init__(self, api: BackendGameLobbyApi) -> None:
        self.api = api

    async def get_view(self, request: Request) -> GameLobbyResponse:
        response = await self.api.get_view(require_access_token(request))
        logger.info("Lobby page view loaded")
        return response

    async def get_status(self, request: Request, char_id: int) -> CharacterStatusDTO:
        response = await self.api.get_status(require_access_token(request), char_id)
        logger.info("Lobby page status loaded: character_id={}", char_id)
        return response

    async def start(self, request: Request, dto: CreateCharacterRequestDTO) -> GameLobbyStartResponse:
        response = await self.api.start(require_access_token(request), dto)
        logger.info("Lobby page character start completed")
        return response

    async def enter(self, request: Request, dto: EnterCharacterRequestDTO) -> GameLobbyEnterResponse:
        response = await self.api.enter(require_access_token(request), dto)
        logger.info("Lobby page character enter completed: character_id={}", dto.character_id)
        return response

    async def release(self, request: Request, dto: EnterCharacterRequestDTO) -> GameLobbyReleaseResponse:
        response = await self.api.release(require_access_token(request), dto)
        logger.info("Lobby page character release completed: character_id={}", dto.character_id)
        return response

    async def delete(self, request: Request, dto: DeleteCharacterRequestDTO) -> GameLobbyResponse:
        response = await self.api.delete(require_access_token(request), dto)
        logger.warning("Lobby page character deleted: character_id={}", dto.character_id)
        return response
