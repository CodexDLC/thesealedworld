from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request
from starlette.responses import Response

from src.frontend.core.api import BaseApiClient
from src.frontend.game_features.session.middleware import GameTokenRefreshMiddleware
from src.frontend.game_features.session.token_state import (
    GAME_ACCESS_COOKIE_NAME,
    GAME_REFRESH_COOKIE_NAME,
    extract_game_tokens,
    require_game_access_token,
    set_game_token_cookies,
)
from src.frontend.integrations.backend_api.game_lobby import GameTokenPair


def test_require_game_access_token_prefers_game_cookie() -> None:
    request = SimpleNamespace(
        cookies={
            "tbmmorpg_access_token": "site-token",
            GAME_ACCESS_COOKIE_NAME: "game-token",
        },
        state=SimpleNamespace(),
    )

    assert require_game_access_token(request) == "game-token"


def test_require_game_access_token_falls_back_to_site_token_during_transition() -> None:
    request = SimpleNamespace(cookies={"tbmmorpg_access_token": "site-token"}, state=SimpleNamespace())

    assert require_game_access_token(request) == "site-token"


def test_require_game_access_token_redirects_to_lobby_without_any_token() -> None:
    request = SimpleNamespace(cookies={}, state=SimpleNamespace())

    with pytest.raises(Exception) as exc:
        require_game_access_token(request, allow_site_fallback=False)

    assert exc.value.headers == {"Location": "/game-lobby"}


def test_extract_game_tokens_reads_payload_extra_data() -> None:
    backend_response = SimpleNamespace(
        payload=SimpleNamespace(
            model_dump=lambda mode: {
                "extra_data": {
                    "game_tokens": {
                        "game_access_token": "game-access",
                        "game_refresh_token": "game-refresh",
                    }
                }
            }
        )
    )

    assert extract_game_tokens(backend_response) == {
        "access_token": "game-access",
        "refresh_token": "game-refresh",
    }


def test_set_game_token_cookies_uses_distinct_cookie_names() -> None:
    from fastapi import Response

    response = Response()

    set_game_token_cookies(response, access_token="game-access", refresh_token="game-refresh")

    cookie_header = "\n".join(value.decode() for key, value in response.raw_headers if key == b"set-cookie")
    assert f"{GAME_ACCESS_COOKIE_NAME}=game-access" in cookie_header
    assert f"{GAME_REFRESH_COOKIE_NAME}=game-refresh" in cookie_header


async def test_base_api_client_adds_internal_service_header() -> None:
    class _Client:
        def __init__(self) -> None:
            self.headers = None

        async def request(self, method, url, **kwargs):
            self.headers = kwargs["headers"]
            return SimpleNamespace(
                status_code=204,
                content=b"",
                raise_for_status=lambda: None,
            )

    client = _Client()
    api = BaseApiClient(
        client=client,
        base_url="http://backend",
        internal_service_key="internal-key",  # pragma: allowlist secret
        internal_service_header="X-Test-Service-Key",
    )

    await api._request("GET", "/health", headers={"Authorization": "Bearer game-token"})

    assert client.headers == {
        "Authorization": "Bearer game-token",
        "X-Test-Service-Key": "internal-key",
    }


async def test_game_token_refresh_middleware_uses_refresh_cookie_when_access_missing(mocker) -> None:
    tokens = GameTokenPair(access_token="new-game-access", refresh_token="new-game-refresh", expires_in=900)
    api_cls = mocker.patch("src.frontend.game_features.session.middleware.BackendGameLobbyApi")
    api_cls.return_value.refresh_token = AsyncMock(return_value=tokens)
    middleware = GameTokenRefreshMiddleware(app=SimpleNamespace())
    request = _starlette_request(
        "/game/session",
        headers=[(b"cookie", f"{GAME_REFRESH_COOKIE_NAME}=old-game-refresh".encode())],
    )
    call_next = AsyncMock(return_value=Response("ok"))

    response = await middleware.dispatch(request, call_next)

    assert request.state.game_access_token == "new-game-access"
    api_cls.return_value.refresh_token.assert_awaited_once_with("old-game-refresh")
    cookie_header = "\n".join(response.headers.getlist("set-cookie"))
    assert f"{GAME_ACCESS_COOKIE_NAME}=new-game-access" in cookie_header
    assert f"{GAME_REFRESH_COOKIE_NAME}=new-game-refresh" in cookie_header


async def test_game_token_refresh_middleware_keeps_fresh_access_cookie(mocker) -> None:
    api_cls = mocker.patch("src.frontend.game_features.session.middleware.BackendGameLobbyApi")
    middleware = GameTokenRefreshMiddleware(app=SimpleNamespace())
    cookie_value = (
        f"{GAME_ACCESS_COOKIE_NAME}={_unsigned_token(exp=4102444800)}; "
        f"{GAME_REFRESH_COOKIE_NAME}=old-game-refresh"
    ).encode()
    request = _starlette_request(
        "/game/session",
        headers=[
            (b"cookie", cookie_value)
        ],
    )
    call_next = AsyncMock(return_value=Response("ok"))

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 200
    assert request.state.game_access_token
    api_cls.assert_not_called()


def _starlette_request(path: str, headers: list[tuple[bytes, bytes]]) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": headers,
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
            "client": ("testclient", 50000),
            "app": SimpleNamespace(state=SimpleNamespace(backend_http_client=object())),
        }
    )


def _unsigned_token(*, exp: int) -> str:
    import base64
    import json

    def encode(payload):
        raw = json.dumps(payload, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    return f"{encode({'alg': 'HS256'})}.{encode({'exp': exp})}.signature"
