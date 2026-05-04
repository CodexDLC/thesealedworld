from fastapi import Request

from src.frontend.integrations.backend_api.game_catalog import BackendGameCatalogApi
from src.frontend.site_features.auth.token_state import require_access_token


class GameCatalogFrontendService:
    def __init__(self, *, api: BackendGameCatalogApi) -> None:
        self.api = api

    async def get_bootstrap(self, request: Request) -> dict:
        return await self.api.get_bootstrap(require_access_token(request))
