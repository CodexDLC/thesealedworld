from typing import Annotated

from fastapi import Depends, Request

from src.frontend.config.settings import settings
from src.frontend.features.auth.dependencies.providers import get_backend_http_client
from src.frontend.game_features.game_catalog.services.catalog_service import GameCatalogFrontendService
from src.frontend.integrations.backend_api.game_catalog import BackendGameCatalogApi


def get_backend_game_catalog_api(request: Request) -> BackendGameCatalogApi:
    return BackendGameCatalogApi(client=get_backend_http_client(request), base_url=settings.backend_base_url)


def get_game_catalog_service(
    api: Annotated[BackendGameCatalogApi, Depends(get_backend_game_catalog_api)],
) -> GameCatalogFrontendService:
    return GameCatalogFrontendService(api=api)
