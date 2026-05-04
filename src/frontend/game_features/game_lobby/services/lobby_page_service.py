from fastapi import HTTPException, Request, status
from loguru import logger

from src.frontend.integrations.backend_api.game_lobby import (
    BackendGameLobbyApi,
    GameLobbyEnterResponse,
    GameLobbyResponse,
    GameLobbyStartResponse,
)
from src.shared.schemas import CreateCharacterRequestDTO, DeleteCharacterRequestDTO, EnterCharacterRequestDTO


class GameLobbyPageService:
    access_cookie_name = "tbmmorpg_access_token"

    def __init__(self, api: BackendGameLobbyApi) -> None:
        self.api = api

    async def get_view(self, request: Request) -> GameLobbyResponse:
        response = await self.api.get_view(self._require_access_token(request))
        logger.info("Lobby page view loaded")
        return response

    async def start(self, request: Request, dto: CreateCharacterRequestDTO) -> GameLobbyStartResponse:
        response = await self.api.start(self._require_access_token(request), dto)
        logger.info("Lobby page character start completed")
        return response

    async def enter(self, request: Request, dto: EnterCharacterRequestDTO) -> GameLobbyEnterResponse:
        response = await self.api.enter(self._require_access_token(request), dto)
        logger.info("Lobby page character enter completed: character_id={}", dto.character_id)
        return response

    async def delete(self, request: Request, dto: DeleteCharacterRequestDTO) -> GameLobbyResponse:
        response = await self.api.delete(self._require_access_token(request), dto)
        logger.warning("Lobby page character deleted: character_id={}", dto.character_id)
        return response

    def _require_access_token(self, request: Request) -> str:
        token = request.cookies.get(self.access_cookie_name)
        if not token:
            logger.warning("Lobby page access rejected: missing_access_token path={}", request.url.path)
            raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
        return token
