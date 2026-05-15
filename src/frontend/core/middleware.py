from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.frontend.core.database import get_session_context
from src.frontend.features.auth.integrations import AuthPersistence
from src.frontend.features.auth.repositories.token_repository import TokenRepository
from src.frontend.features.auth.repositories.user_repository import UserRepository
from src.frontend.features.auth.services.auth_service import FrontendAuthService

ANALYTICS_SKIP_PREFIXES = ("/static/", "/library/", "/cabinet/", "/health")
ANALYTICS_EVENT_PATHS: dict[str, str] = {
    "/auth/register": "registrations",
    "/lobby": "lobby_visits",
    "/game/join": "game_joins",
}


class SiteAnalyticsMiddleware(BaseHTTPMiddleware):
    """Increments in-memory counters for key site events. Fire-and-forget, never blocks."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if not path.startswith(ANALYTICS_SKIP_PREFIXES):
            counters: dict[str, int] = getattr(request.app.state, "site_analytics", {})
            counters["visits"] = counters.get("visits", 0) + 1
            event_key = ANALYTICS_EVENT_PATHS.get(path)
            if event_key:
                counters[event_key] = counters.get(event_key, 0) + 1
        return await call_next(request)


AUTH_LOOKUP_SKIP_EXACT_PATHS = {
    "/favicon.ico",
    "/health",
    "/library",
}
AUTH_LOOKUP_SKIP_PATH_PREFIXES = (
    "/library/",
    "/static/",
)


def should_skip_auth_lookup(path: str) -> bool:
    return path in AUTH_LOOKUP_SKIP_EXACT_PATHS or path.startswith(AUTH_LOOKUP_SKIP_PATH_PREFIXES)


class AuthUserMiddleware(BaseHTTPMiddleware):
    """Silently resolves the current user from the access token cookie
    and attaches it to request.state.user for every request.
    Never blocks the request — unauthenticated state is just user=None."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.user = None
        if should_skip_auth_lookup(request.url.path):
            return await call_next(request)

        if not request.cookies.get(FrontendAuthService.access_cookie_name) and not request.cookies.get(
            FrontendAuthService.refresh_cookie_name
        ):
            return await call_next(request)

        try:
            async with get_session_context() as session:
                auth_service = FrontendAuthService(
                    auth_service=import_site_auth_service(session),
                )
                request.state.user = await auth_service.get_current_user(request)
            if request.state.user is not None and not getattr(request.state, "access_token", None):
                cookie_token = request.cookies.get(FrontendAuthService.access_cookie_name)
                if cookie_token:
                    request.state.access_token = cookie_token
        except Exception as exc:
            logger.warning("Auth middleware user lookup failed: error={}", exc)

        response = await call_next(request)
        tokens = getattr(request.state, "auth_tokens", None)
        if tokens is not None:
            response.set_cookie(
                FrontendAuthService.access_cookie_name,
                tokens.access_token,
                httponly=True,
                samesite="lax",
                secure=False,
                max_age=60 * 30,
            )
            response.set_cookie(
                FrontendAuthService.refresh_cookie_name,
                tokens.refresh_token,
                httponly=True,
                samesite="lax",
                secure=False,
                max_age=60 * 60 * 24 * 30,
            )
        elif getattr(request.state, "clear_auth_cookies", False):
            response.delete_cookie(FrontendAuthService.access_cookie_name)
            response.delete_cookie(FrontendAuthService.refresh_cookie_name)
        return response


def import_site_auth_service(session):
    from src.frontend.features.auth.services.site_auth_service import AuthService

    return AuthService(persistence=AuthPersistence(UserRepository(session), TokenRepository(session)))
