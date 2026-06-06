from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.testclient import TestClient

from src.frontend.config.settings import settings
from src.frontend.core.renderer import get_ui_renderer
from src.frontend.features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.game_features.game_lobby.dependencies.providers import get_game_lobby_page_service
from src.frontend.game_features.game_lobby.routes.pages import router
from src.frontend.integrations.backend_api.game_lobby import GameLobbyPayload, GameLobbyResponse, LobbySlotPayload
from src.shared.enums.domain_enums import CoreDomain
from src.shared.schemas.response import GameStateHeader


def test_play_surface_guest_lobby_redirects_to_site_login_expired(monkeypatch) -> None:
    """Unauth user on play.* must land on site /login?expired=1, NOT site /play.

    Redirecting to /play loops because site /play sees the still-valid access
    cookie, treats the user as authed, and bounces back into the lobby —
    ERR_TOO_MANY_REDIRECTS. /login?expired=1 clears the cookies and stops.
    """
    monkeypatch.setattr(settings, "frontend_surface", "play")
    monkeypatch.setattr(settings, "site_base_url", "http://localhost:8080")
    app = _make_app(user=None)

    response = TestClient(app).get(
        "/game-lobby",
        headers={"host": "play.localhost:8080", "x-forwarded-proto": "http"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "http://localhost:8080/login?expired=1"
    assert "THE BOND: RESONANCE" not in response.text


def test_play_surface_guest_lobby_infers_site_login_from_play_host(monkeypatch) -> None:
    monkeypatch.setattr(settings, "frontend_surface", "play")
    monkeypatch.setattr(settings, "site_base_url", "")
    app = _make_app(user=None)

    response = TestClient(app).get(
        "/game-lobby",
        headers={"host": "play.thesealed.localhost:8080", "x-forwarded-proto": "http"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "http://thesealed.localhost:8080/login?expired=1"


def test_play_surface_lobby_close_returns_to_site_origin_from_query(monkeypatch) -> None:
    monkeypatch.setattr(settings, "frontend_surface", "play")
    monkeypatch.setattr(settings, "site_base_url", "http://thesealed.localhost:8080")
    app = _make_app(user=SimpleNamespace(id=1, email="tester@example.test"))

    response = TestClient(app).get(
        "/game-lobby?return_to=http%3A%2F%2Flocalhost%3A8080%2F",
        headers={"host": "play.thesealed.localhost:8080", "x-forwarded-proto": "http"},
    )

    assert response.status_code == 200
    assert response.json()["context"]["lobby_close_url"] == "http://localhost:8080/"


def test_play_surface_lobby_close_falls_back_to_site_host(monkeypatch) -> None:
    monkeypatch.setattr(settings, "frontend_surface", "play")
    monkeypatch.setattr(settings, "site_base_url", "")
    app = _make_app(user=SimpleNamespace(id=1, email="tester@example.test"))

    response = TestClient(app).get(
        "/game-lobby",
        headers={"host": "play.thesealed.localhost:8080", "x-forwarded-proto": "http"},
    )

    assert response.status_code == 200
    assert response.json()["context"]["lobby_close_url"] == "http://thesealed.localhost:8080/"


def _make_app(user=None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    class AuthServiceStub:
        async def get_current_user(self, request):
            return user

    class UIRendererStub:
        async def render(self, template_name, context=None, status_code=200):
            context = context or {}
            return JSONResponse(
                {"template": template_name, "context": {"lobby_close_url": context.get("lobby_close_url")}},
                status_code=status_code,
            )

    class LobbyServiceStub:
        async def get_view(self, user):
            return GameLobbyResponse(
                header=GameStateHeader(current_state=CoreDomain.LOBBY),
                payload=GameLobbyPayload(
                    title="Порог",
                    description="Врата молчат.",
                    primary_action_label="Играть",
                    primary_action="enter",
                    slots=[
                        LobbySlotPayload(
                            index=1,
                            is_empty=False,
                            character_id="1",
                            name="Codexen",
                            status="lobby",
                        ),
                    ],
                ),
            )

    app.dependency_overrides[get_frontend_auth_service] = lambda: AuthServiceStub()
    app.dependency_overrides[get_ui_renderer] = lambda: UIRendererStub()
    app.dependency_overrides[get_game_lobby_page_service] = lambda: LobbyServiceStub()
    return app
