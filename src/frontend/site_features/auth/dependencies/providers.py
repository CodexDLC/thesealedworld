import httpx
from fastapi import Request

from src.frontend.config.settings import settings
from src.frontend.integrations.backend_api.auth import BackendAuthApi
from src.frontend.site_features.auth.services.auth_service import FrontendAuthService


def get_backend_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.backend_http_client


def get_backend_auth_api(request: Request) -> BackendAuthApi:
    return BackendAuthApi(client=get_backend_http_client(request), base_url=settings.backend_base_url)


def get_frontend_auth_service(request: Request) -> FrontendAuthService:
    return FrontendAuthService(auth_api=get_backend_auth_api(request))
