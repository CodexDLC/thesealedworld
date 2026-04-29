import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.frontend.config.settings import settings
from src.frontend.integrations.backend_api.auth import BackendAuthApi


class AuthUserMiddleware(BaseHTTPMiddleware):
    """Silently resolves the current user from the access token cookie
    and attaches it to request.state.user for every request.
    Never blocks the request — unauthenticated state is just user=None."""

    ACCESS_COOKIE = "tbmmorpg_access_token"

    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.user = None
        token = request.cookies.get(self.ACCESS_COOKIE)
        if token:
            try:
                client: httpx.AsyncClient = request.app.state.backend_http_client
                api = BackendAuthApi(client=client, base_url=settings.backend_base_url)
                request.state.user = await api.current_user(token)
            except (httpx.HTTPStatusError, httpx.RequestError):
                pass
        return await call_next(request)
