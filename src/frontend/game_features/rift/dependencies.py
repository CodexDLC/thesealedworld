from fastapi import Request

from src.frontend.config.settings import settings
from src.frontend.features.auth.dependencies.providers import get_backend_http_client
from src.frontend.integrations.backend_api.character_status import BackendCharacterStatusApi
from src.frontend.integrations.backend_api.inventory import BackendInventoryApi
from src.frontend.integrations.backend_api.rift import BackendRiftApi
from src.frontend.integrations.backend_api.rift_dev import BackendRiftDevApi


def get_backend_character_status_api(request: Request) -> BackendCharacterStatusApi:
    return BackendCharacterStatusApi(client=get_backend_http_client(request), base_url=settings.backend_base_url)


def get_backend_inventory_api(request: Request) -> BackendInventoryApi:
    return BackendInventoryApi(client=get_backend_http_client(request), base_url=settings.backend_base_url)


def get_backend_rift_api(request: Request) -> BackendRiftApi:
    return BackendRiftApi(client=get_backend_http_client(request), base_url=settings.backend_base_url)


def get_backend_rift_dev_api(request: Request) -> BackendRiftDevApi:
    return BackendRiftDevApi(client=get_backend_http_client(request), base_url=settings.backend_base_url)
