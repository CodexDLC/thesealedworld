from fastapi import Request

from src.frontend.game_features.session.token_state import require_game_access_token
from src.frontend.integrations.backend_api.game_catalog import BackendGameCatalogApi


class GameCatalogFrontendService:
    def __init__(self, *, api: BackendGameCatalogApi) -> None:
        self.api = api

    async def get_bootstrap(self, request: Request) -> dict:
        return await self.api.get_bootstrap(require_game_access_token(request))
