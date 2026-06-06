from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlsplit

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from starlette.testclient import TestClient

from src.frontend.app import inline_css
from src.frontend.config.settings import settings
from src.frontend.features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.features.public_site.routes.pages import router


def _make_app(user=None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    templates = Jinja2Templates(directory=str(settings.templates_dir))
    templates.env.globals["inline_css"] = inline_css
    app.state.templates = templates

    class AuthServiceStub:
        async def get_current_user(self, request):
            return user

    app.dependency_overrides[get_frontend_auth_service] = lambda: AuthServiceStub()

    @app.middleware("http")
    async def inject_user(request, call_next):
        request.state.user = user
        request.state.game_menu_service = None
        return await call_next(request)

    return app


def test_play_entry_redirects_authenticated_user_to_public_play_url(monkeypatch) -> None:
    monkeypatch.setattr(settings, "play_public_base_url", "http://127.0.0.1:8003")
    app = _make_app(user=SimpleNamespace(email="tester@example.test"))

    with patch(
        "src.frontend.features.public_site.routes.pages.PlayAvailabilityService.is_available",
        new=AsyncMock(return_value=True),
    ):
        response = TestClient(app).get("/play", follow_redirects=False)

    assert response.status_code == 303
    location = response.headers["location"]
    parsed = urlsplit(location)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == "http://127.0.0.1:8003/game-lobby"
    assert parse_qs(parsed.query) == {"return_to": ["http://testserver/"]}


def test_play_entry_renders_maintenance_when_play_is_down() -> None:
    app = _make_app(user=SimpleNamespace(email="tester@example.test"))

    with patch(
        "src.frontend.features.public_site.routes.pages.PlayAvailabilityService.is_available",
        new=AsyncMock(return_value=False),
    ):
        response = TestClient(app, raise_server_exceptions=False).get("/play")

    assert response.status_code == 503
    assert "Игровой сервер недоступен - The Sealed World" in response.text
    assert 'content="noindex, nofollow"' in response.text
    assert "Врата временно закрыты" in response.text
    assert "Игровое лобби сейчас не отвечает" in response.text
    assert "<dt>Сайт</dt>" in response.text
    assert "<dd>Доступен</dd>" in response.text
    assert "<dt>Аккаунт</dt>" not in response.text
    assert "<dt>Игра</dt>" in response.text
    assert "<dd>Недоступна</dd>" in response.text
    assert "page-play-unavailable" in response.text
    assert "tsw-hero" not in response.text


def test_play_entry_opens_login_for_anonymous_user(monkeypatch) -> None:
    monkeypatch.setattr(settings, "site_base_url", "http://thesealed.localhost:8080")
    app = _make_app(user=None)

    with patch(
        "src.frontend.features.public_site.routes.pages.PlayAvailabilityService.is_available",
        new=AsyncMock(return_value=True),
    ):
        response = TestClient(app, raise_server_exceptions=False).get("/play")

    assert response.status_code == 200
    assert "THE BOND: RESONANCE" in response.text
    assert 'class="auth-modal-close" href="/"' in response.text
    assert 'class="auth-modal-scrim" href="/"' in response.text
    assert "client-auth-modal-title" not in response.text


def test_play_entry_renders_maintenance_before_login_when_play_is_down() -> None:
    app = _make_app(user=None)

    with patch(
        "src.frontend.features.public_site.routes.pages.PlayAvailabilityService.is_available",
        new=AsyncMock(return_value=False),
    ):
        response = TestClient(app, raise_server_exceptions=False).get("/play")

    assert response.status_code == 503
    assert "Врата временно закрыты" in response.text
    assert "THE BOND: RESONANCE" not in response.text
