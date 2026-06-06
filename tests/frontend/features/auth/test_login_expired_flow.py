"""Loop-breaker tests for the play↔site redirect bug."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from starlette.testclient import TestClient

from src.frontend.app import inline_css
from src.frontend.config.settings import settings


def _make_play_app(*, user=None) -> FastAPI:
    """Mount only the game-lobby router with play-surface behavior."""
    from src.frontend.game_features.game_lobby.routes.pages import router

    app = FastAPI()
    app.include_router(router)
    templates = Jinja2Templates(directory=str(settings.templates_dir))
    templates.env.globals["inline_css"] = inline_css
    app.state.templates = templates

    @app.middleware("http")
    async def inject_user(request, call_next):
        request.state.user = user
        request.state.game_menu_service = None
        return await call_next(request)

    return app


@pytest.mark.unit
def test_play_game_lobby_redirects_unauth_user_to_site_login_expired(monkeypatch):
    """
    Critical loop-breaker: when play /game-lobby sees user=None, it must NOT
    redirect to site/play (which sees a still-valid access cookie and bounces
    back, producing ERR_TOO_MANY_REDIRECTS). Target is /login?expired=1.
    """
    monkeypatch.setattr(settings, "frontend_surface", "play", raising=False)
    monkeypatch.setattr(settings, "site_base_url", "http://thesealed.localhost:8080", raising=False)

    from src.frontend.features.auth.dependencies.providers import get_frontend_auth_service
    from src.frontend.game_features.game_lobby.dependencies.providers import (
        get_game_lobby_page_service,
    )

    app = _make_play_app(user=None)

    fake_auth_service = MagicMock()
    fake_auth_service.get_current_user = AsyncMock(return_value=None)
    fake_lobby_service = MagicMock()
    app.dependency_overrides[get_frontend_auth_service] = lambda: fake_auth_service
    app.dependency_overrides[get_game_lobby_page_service] = lambda: fake_lobby_service

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/game-lobby", follow_redirects=False)

    assert response.status_code == 303, response.text[:500]
    location = response.headers["location"]
    assert location.endswith("/login?expired=1"), location
    # The whole point of the fix: must NOT bounce back to /play
    redirect_path = location.split("?", 1)[0].rsplit("/", 1)[-1]
    assert redirect_path == "login", location


@pytest.mark.unit
def test_login_page_with_expired_clears_session_cookies(monkeypatch):
    """GET /login?expired=1 must explicitly clear the session cookies."""
    from src.frontend.features.auth.routes.pages import router as auth_router

    monkeypatch.setattr(settings, "auth_cookie_domain", ".thesealed.localhost", raising=False)

    app = FastAPI()
    app.include_router(auth_router)
    templates = Jinja2Templates(directory=str(settings.templates_dir))
    templates.env.globals["inline_css"] = inline_css
    app.state.templates = templates

    @app.middleware("http")
    async def state_defaults(request, call_next):
        request.state.user = None
        request.state.game_menu_service = None
        return await call_next(request)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(
        "/login?expired=1",
        cookies={
            "tbmmorpg_access_token": "stale",
            "tbmmorpg_refresh_token": "stale",
            "tbmmorpg_active_character": "x",
        },
    )
    assert response.status_code == 200

    set_cookies = response.headers.get_list("set-cookie")
    cleared = [c for c in set_cookies if "Max-Age=0" in c or 'expires=Thu, 01 Jan 1970' in c.lower()]
    cleared_names = {c.split("=", 1)[0] for c in cleared}
    assert "tbmmorpg_access_token" in cleared_names
    assert "tbmmorpg_refresh_token" in cleared_names


@pytest.mark.unit
def test_login_page_with_expired_renders_session_expired_banner():
    from src.frontend.features.auth.routes.pages import router as auth_router

    app = FastAPI()
    app.include_router(auth_router)
    templates = Jinja2Templates(directory=str(settings.templates_dir))
    templates.env.globals["inline_css"] = inline_css
    app.state.templates = templates

    @app.middleware("http")
    async def state_defaults(request, call_next):
        request.state.user = None
        request.state.game_menu_service = None
        return await call_next(request)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/login?expired=1")
    assert response.status_code == 200
    assert "Сессия истекла" in response.text


@pytest.mark.unit
def test_login_page_without_expired_does_not_render_banner():
    from src.frontend.features.auth.routes.pages import router as auth_router

    app = FastAPI()
    app.include_router(auth_router)
    templates = Jinja2Templates(directory=str(settings.templates_dir))
    templates.env.globals["inline_css"] = inline_css
    app.state.templates = templates

    @app.middleware("http")
    async def state_defaults(request, call_next):
        request.state.user = None
        request.state.game_menu_service = None
        return await call_next(request)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/login")
    assert response.status_code == 200
    assert "Сессия истекла" not in response.text
