from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request
from starlette.responses import Response

from src.frontend.core.middleware import AuthUserMiddleware, should_skip_auth_lookup


@pytest.mark.parametrize(
    "path",
    [
        "/health",
        "/favicon.ico",
        "/static/css/game.css",
        "/static/js/game.js",
        "/static/images/ui/game-menu-icons/inventory.svg",
        "/static/images/ui/textures/button.webp",
    ],
)
def test_should_skip_auth_lookup_for_public_technical_paths(path: str) -> None:
    assert should_skip_auth_lookup(path)


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/login",
        "/cabinet",
        "/game/session",
        "/game/catalog/bootstrap",
        "/game/character-status/panel",
        "/api/game/character-status",
    ],
)
def test_should_not_skip_auth_lookup_for_page_and_game_paths(path: str) -> None:
    assert not should_skip_auth_lookup(path)


async def test_auth_middleware_does_not_build_backend_auth_for_static_path(mocker) -> None:
    auth_service = mocker.patch("src.frontend.core.middleware.FrontendAuthService")
    middleware = AuthUserMiddleware(app=SimpleNamespace())
    request = _request_for_path("/static/js/game.js")
    call_next = AsyncMock(return_value=Response("ok"))

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 200
    auth_service.assert_not_called()
    call_next.assert_awaited_once_with(request)


async def test_auth_middleware_skips_lookup_when_no_auth_cookies(mocker) -> None:
    auth_service_cls = mocker.patch("src.frontend.core.middleware.FrontendAuthService")
    middleware = AuthUserMiddleware(app=SimpleNamespace())
    request = _request_for_path("/game-lobby")
    call_next = AsyncMock(return_value=Response("ok"))

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 200
    assert request.state.user is None
    auth_service_cls.assert_not_called()
    call_next.assert_awaited_once_with(request)


async def test_auth_middleware_resolves_user_from_cookie(mocker) -> None:
    user = SimpleNamespace(id="user-1", email="test@example.com")
    service = SimpleNamespace(get_current_user=AsyncMock(return_value=user))
    auth_service_cls = mocker.patch("src.frontend.core.middleware.FrontendAuthService", return_value=service)
    auth_service_cls.access_cookie_name = "access"
    auth_service_cls.refresh_cookie_name = "refresh"
    mocker.patch("src.frontend.core.middleware.import_site_auth_service", return_value=object())
    mocker.patch("src.frontend.core.middleware.get_session_context", return_value=_SessionContext())
    middleware = AuthUserMiddleware(app=SimpleNamespace())
    request = _request_for_path("/game/session", headers=[(b"cookie", b"access=token")])
    call_next = AsyncMock(return_value=Response("ok"))

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 200
    assert request.state.user is user
    assert request.state.access_token == "token"
    auth_service_cls.assert_called_once()
    service.get_current_user.assert_awaited_once_with(request)


def _request_for_path(path: str, headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": headers or [],
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
            "client": ("testclient", 50000),
            "app": SimpleNamespace(state=SimpleNamespace()),
        }
    )


class _SessionContext:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, tb):
        return False
