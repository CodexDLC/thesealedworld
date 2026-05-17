from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException, status
from starlette.datastructures import Headers

from src.frontend.app import backend_http_status_handler, frontend_http_exception_handler, split_bracket_coords_label


def test_split_bracket_coords_label_separates_location_suffix() -> None:
    assert split_bracket_coords_label("Причальный Узел [52:52]") == {
        "label": "Причальный Узел",
        "coords": "52:52",
    }


def test_split_bracket_coords_label_preserves_non_coordinate_brackets() -> None:
    assert split_bracket_coords_label("Схватка [1x1]") == {"label": "Схватка [1x1]", "coords": None}


@pytest.mark.asyncio
async def test_backend_401_on_game_page_redirects_to_lobby_and_clears_game_state() -> None:
    request = _request("/game/session")
    backend_request = httpx.Request("GET", "http://backend:8001/game-session/enter")
    backend_response = httpx.Response(status.HTTP_401_UNAUTHORIZED, request=backend_request)
    exc = httpx.HTTPStatusError("unauthorized", request=backend_request, response=backend_response)

    response = await backend_http_status_handler(request, exc)

    assert response.status_code == status.HTTP_303_SEE_OTHER
    assert response.headers["location"] == "/game-lobby"
    cookie_header = "\n".join(response.headers.getlist("set-cookie"))
    assert "tbmmorpg_game_access_token=" in cookie_header
    assert "tbmmorpg_game_refresh_token=" in cookie_header
    assert "tbmmorpg_active_character_id=" in cookie_header


@pytest.mark.asyncio
async def test_frontend_login_redirect_clears_site_auth_cookies() -> None:
    request = _request("/admin")

    response = await frontend_http_exception_handler(
        request,
        HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"}),
    )

    assert response.status_code == status.HTTP_303_SEE_OTHER
    assert response.headers["location"] == "/login"
    cookie_header = "\n".join(response.headers.getlist("set-cookie"))
    assert "tbmmorpg_access_token=" in cookie_header
    assert "tbmmorpg_refresh_token=" in cookie_header


@pytest.mark.asyncio
async def test_backend_401_on_htmx_game_action_sets_hx_redirect() -> None:
    request = _request("/api/game/character-status", headers=[(b"hx-request", b"true")])
    backend_request = httpx.Request("GET", "http://backend:8001/character/status")
    backend_response = httpx.Response(status.HTTP_401_UNAUTHORIZED, request=backend_request)
    exc = httpx.HTTPStatusError("unauthorized", request=backend_request, response=backend_response)

    response = await backend_http_status_handler(request, exc)

    assert response.headers["location"] == "/game-lobby"
    assert response.headers["hx-redirect"] == "/game-lobby"


def _request(path: str, headers: list[tuple[bytes, bytes]] | None = None):
    return SimpleNamespace(
        method="GET",
        url=SimpleNamespace(path=path),
        headers=Headers(raw=headers or []),
    )
