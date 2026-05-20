import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from src.frontend.features.account.routes.pages import router


def _make_app(user=None):
    from fastapi import FastAPI
    from fastapi.templating import Jinja2Templates
    from src.frontend.config.settings import settings
    from src.frontend.app import inline_css

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


def _user_mock(*, tester_status="none", tester_approved_at=None):
    return MagicMock(
        id=uuid.uuid4(),
        email="test@example.com",
        is_active=True,
        is_superuser=False,
        tester_status=tester_status,
        tester_approved_at=tester_approved_at,
        created_at=datetime(2026, 5, 1),
    )


@pytest.mark.unit
class TestAccountRoutes:
    def test_account_redirects_to_profile(self):
        app = _make_app(user=_user_mock())
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/account", follow_redirects=False)
        assert response.status_code == 307
        assert "/account/profile" in response.headers["location"]

    def test_profile_page_returns_200_for_authenticated_user(self):
        app = _make_app(user=_user_mock())
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/account/profile")
        assert response.status_code == 200

    def test_profile_page_redirects_anonymous_to_login(self):
        app = _make_app(user=None)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/account/profile", follow_redirects=False)
        assert response.status_code == 303
        assert "/login" in response.headers["location"]


@pytest.mark.unit
class TestApplyTesterRoute:
    @patch("src.frontend.features.account.routes.pages.get_db")
    def test_apply_tester_post_redirects_to_profile(self, mock_get_db):
        user = _user_mock(tester_status="none")
        app = _make_app(user=user)

        mock_session = AsyncMock()
        mock_get_db.return_value = mock_session

        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_by_id.return_value = MagicMock(
            id=user.id, tester_status="none",
        )
        mock_repo_instance.update_tester_status = AsyncMock()
        mock_repo_instance.commit = AsyncMock()

        with patch(
            "src.frontend.features.account.routes.pages.UserRepository",
            return_value=mock_repo_instance,
        ):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/account/apply-tester", follow_redirects=False)

        assert response.status_code == 303
        assert "/account/profile" in response.headers["location"]

    def test_apply_tester_post_anonymous_redirects_to_login(self):
        app = _make_app(user=None)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/account/apply-tester", follow_redirects=False)
        assert response.status_code == 303
        assert "/login" in response.headers["location"]
