from fastapi import Request

from src.frontend.config.settings import settings
from src.frontend.integrations.backend_api.inventory import BackendInventoryApi
from src.frontend.site_features.auth.dependencies.providers import get_backend_http_client


def get_backend_inventory_api(request: Request) -> BackendInventoryApi:
    return BackendInventoryApi(client=get_backend_http_client(request), base_url=settings.backend_base_url)
