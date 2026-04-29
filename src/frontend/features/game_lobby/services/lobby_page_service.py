from fastapi import HTTPException, Request, status

from src.frontend.integrations.backend_api.game_lobby import BackendGameLobbyApi, GameLobbyResponse


class GameLobbyPageService:
    access_cookie_name = "tbmmorpg_access_token"

    def __init__(self, api: BackendGameLobbyApi) -> None:
        self.api = api

    async def get_view(self, request: Request) -> GameLobbyResponse:
        return await self.api.get_view(self._require_access_token(request))

    async def start(self, request: Request) -> GameLobbyResponse:
        return await self.api.start(self._require_access_token(request))

    def _require_access_token(self, request: Request) -> str:
        token = request.cookies.get(self.access_cookie_name)
        if not token:
            raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
        return token
