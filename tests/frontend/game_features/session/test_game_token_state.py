from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request
from starlette.responses import Response

from src.frontend.core.api import BaseApiClient
from src.frontend.game_features.session.middleware import GameTokenRefreshMiddleware
from src.frontend.game_features.session.routes.pages import _ensure_game_tokens_for_active_character, game_keepalive
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


async def test_game_token_refresh_middleware_keeps_cookies_on_network_error(mocker) -> None:
    """Transient network failures (backend down) must NOT clear the player's
    cookies. The next request will retry with the same refresh token; an
    unrelated outage shouldn't log the player out of the game."""
    import httpx

    api_cls = mocker.patch("src.frontend.game_features.session.middleware.BackendGameLobbyApi")
    api_cls.return_value.refresh_token = AsyncMock(
        side_effect=httpx.ConnectError("backend unreachable")
    )
    middleware = GameTokenRefreshMiddleware(app=SimpleNamespace())
    request = _starlette_request(
        "/game/session",
        headers=[(b"cookie", f"{GAME_REFRESH_COOKIE_NAME}=existing-refresh".encode())],
    )

    await middleware._refresh_if_needed(request)

    assert getattr(request.state, "clear_game_token_cookies", False) is False


async def test_game_token_refresh_middleware_clears_cookies_on_4xx(mocker) -> None:
    """4xx from backend means the refresh token itself is invalid/replaced.
    Clear cookies so the next request bounces to login cleanly."""
    import httpx

    api_cls = mocker.patch("src.frontend.game_features.session.middleware.BackendGameLobbyApi")
    fake_response = httpx.Response(status_code=401, request=httpx.Request("POST", "http://backend/refresh"))
    api_cls.return_value.refresh_token = AsyncMock(
        side_effect=httpx.HTTPStatusError("rejected", request=fake_response.request, response=fake_response)
    )
    middleware = GameTokenRefreshMiddleware(app=SimpleNamespace())
    request = _starlette_request(
        "/game/session",
        headers=[(b"cookie", f"{GAME_REFRESH_COOKIE_NAME}=stale-refresh".encode())],
    )

    await middleware._refresh_if_needed(request)

    assert request.state.clear_game_token_cookies is True


async def test_game_token_refresh_middleware_keeps_cookies_on_5xx(mocker) -> None:
    """5xx from backend is also transient (backend bug, redis down). Don't
    punish the player by wiping their session cookies."""
    import httpx

    api_cls = mocker.patch("src.frontend.game_features.session.middleware.BackendGameLobbyApi")
    fake_response = httpx.Response(status_code=502, request=httpx.Request("POST", "http://backend/refresh"))
    api_cls.return_value.refresh_token = AsyncMock(
        side_effect=httpx.HTTPStatusError("bad gateway", request=fake_response.request, response=fake_response)
    )
    middleware = GameTokenRefreshMiddleware(app=SimpleNamespace())
    request = _starlette_request(
        "/game/session",
        headers=[(b"cookie", f"{GAME_REFRESH_COOKIE_NAME}=existing-refresh".encode())],
    )

    await middleware._refresh_if_needed(request)

    assert getattr(request.state, "clear_game_token_cookies", False) is False


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


async def test_game_session_reissues_tokens_when_active_character_has_only_site_cookie() -> None:
    tokens_response = SimpleNamespace(payload={"game_tokens": {"access_token": "game-access", "refresh_token": "game-refresh"}})
    lobby_service = SimpleNamespace(select=AsyncMock(return_value=tokens_response))
    request = SimpleNamespace(cookies={"tbmmorpg_access_token": "site-token"}, state=SimpleNamespace())
    user = SimpleNamespace()

    tokens = await _ensure_game_tokens_for_active_character(
        request,
        user=user,
        char_id=7,
        lobby_service=lobby_service,
    )

    assert tokens == {"access_token": "game-access", "refresh_token": "game-refresh"}
    assert request.state.game_access_token == "game-access"
    lobby_service.select.assert_awaited_once()
    assert lobby_service.select.await_args.args[1].character_id == 7


async def test_game_session_keeps_existing_game_cookie_without_reselecting() -> None:
    lobby_service = SimpleNamespace(select=AsyncMock())
    request = SimpleNamespace(cookies={GAME_ACCESS_COOKIE_NAME: "game-access"}, state=SimpleNamespace())

    tokens = await _ensure_game_tokens_for_active_character(
        request,
        user=SimpleNamespace(),
        char_id=7,
        lobby_service=lobby_service,
    )

    assert tokens is None
    lobby_service.select.assert_not_called()


async def test_keepalive_returns_204_when_middleware_already_refreshed_token() -> None:
    """Healthy path: GameTokenRefreshMiddleware ran before the handler and
    populated request.state.game_access_token from the refresh-token flow.
    The handler just confirms with 204 — it must NOT call lobby_service.select
    (that would mint a new session_id and stomp the lock)."""
    auth_service = SimpleNamespace(get_current_user=AsyncMock(return_value=SimpleNamespace()))
    request = SimpleNamespace(
        cookies={
            "tbmmorpg_access_token": "site-token",
            "tbmmorpg_active_character_id": "7",
            GAME_ACCESS_COOKIE_NAME: "fresh-game",
        },
        state=SimpleNamespace(game_access_token="fresh-game"),
    )

    response = await game_keepalive(request, auth_service=auth_service)

    assert response.status_code == 204


async def test_keepalive_returns_401_when_middleware_gave_up() -> None:
    """If middleware set ``clear_game_token_cookies`` (refresh rejected), the
    supervisor must see a non-2xx so it bails to the lobby instead of looping."""
    auth_service = SimpleNamespace(get_current_user=AsyncMock(return_value=SimpleNamespace()))
    request = SimpleNamespace(
        cookies={
            "tbmmorpg_access_token": "site-token",
            "tbmmorpg_active_character_id": "7",
        },
        state=SimpleNamespace(clear_game_token_cookies=True),
    )

    response = await game_keepalive(request, auth_service=auth_service)

    assert response.status_code == 401


async def test_keepalive_returns_401_when_no_game_token_available() -> None:
    auth_service = SimpleNamespace(get_current_user=AsyncMock(return_value=SimpleNamespace()))
    request = SimpleNamespace(
        cookies={
            "tbmmorpg_access_token": "site-token",
            "tbmmorpg_active_character_id": "7",
        },
        state=SimpleNamespace(),
    )

    response = await game_keepalive(request, auth_service=auth_service)

    assert response.status_code == 401


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
