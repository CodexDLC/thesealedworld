from typing import Annotated

from fastapi import Depends, Request

from src.frontend.config.settings import settings
from src.frontend.features.auth.dependencies.providers import get_backend_http_client
from src.frontend.game_features.character_status.services.status_panel_service import StatusPanelService
from src.frontend.integrations.backend_api.character_status import BackendCharacterStatusApi


def get_backend_character_status_api(request: Request) -> BackendCharacterStatusApi:
    return BackendCharacterStatusApi(client=get_backend_http_client(request), base_url=settings.backend_base_url)


def get_status_panel_service(
    api: Annotated[BackendCharacterStatusApi, Depends(get_backend_character_status_api)],
) -> StatusPanelService:
    return StatusPanelService(api=api)
