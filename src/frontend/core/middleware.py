import httpx
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.frontend.config.settings import settings
from src.frontend.integrations.backend_api.auth import BackendAuthApi
from src.frontend.site_features.auth.services.auth_service import FrontendAuthService


class AuthUserMiddleware(BaseHTTPMiddleware):
    """Silently resolves the current user from the access token cookie
    and attaches it to request.state.user for every request.
    Never blocks the request — unauthenticated state is just user=None."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.user = None
        try:
            client: httpx.AsyncClient = request.app.state.backend_http_client
            api = BackendAuthApi(client=client, base_url=settings.backend_base_url)
            auth_service = FrontendAuthService(auth_api=api)
            request.state.user = await auth_service.get_current_user(request)
        except httpx.RequestError:
            logger.opt(exception=True).critical("Auth middleware backend user lookup failed")

        response = await call_next(request)
        tokens = getattr(request.state, "auth_tokens", None)
        if tokens is not None:
            FrontendAuthService(auth_api=api).attach_auth_cookies(response, tokens)
        elif getattr(request.state, "clear_auth_cookies", False):
            response.delete_cookie(FrontendAuthService.access_cookie_name)
            response.delete_cookie(FrontendAuthService.refresh_cookie_name)
        return response
