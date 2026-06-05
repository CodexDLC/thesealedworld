import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from src.frontend.core.database import get_db
from src.frontend.features.account.routes.pages import router


def _make_app(user=None):
    from fastapi import FastAPI
    from fastapi.templating import Jinja2Templates

    from src.frontend.app import inline_css
    from src.frontend.config.settings import settings

    app = FastAPI()
    app.include_router(router)
    templates = Jinja2Templates(directory=str(settings.templates_dir))
    templates.env.globals["inline_css"] = inline_css
    app.state.templates = templates

    async def _fake_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = _fake_db

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
        referral_code="SEAL-TESTCODE",
        created_at=datetime(2026, 5, 1),
    )


def _patch_repo():
    mock_repo = AsyncMock()
    mock_repo.get_referral_stats = AsyncMock(return_value={"invited": 0, "active": 0, "bonus": 0})
    return patch("src.frontend.features.account.routes.pages.UserRepository", return_value=mock_repo)


@pytest.mark.unit
class TestAccountRoutes:
    def test_account_redirects_to_profile(self):
        app = _make_app(user=_user_mock())
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/account", follow_redirects=False)
        assert response.status_code == 303
        assert "/account/profile" in response.headers["location"]

    def test_profile_page_returns_200_for_authenticated_user(self):
        app = _make_app(user=_user_mock())
        client = TestClient(app, raise_server_exceptions=False)
        with _patch_repo():
            response = client.get("/account/profile")
        assert response.status_code == 200
        assert "Мой аккаунт" in response.text
        assert "Персонажи" in response.text
        assert "Рефералы" in response.text
        assert "Платежи" in response.text
        assert "Подать заявку на тестирование" not in response.text
        assert "Хотите помочь с тестированием" not in response.text

    def test_profile_page_renders_selected_section_only(self):
        app = _make_app(user=_user_mock())
        client = TestClient(app, raise_server_exceptions=False)
        with _patch_repo():
            response = client.get("/account/profile?section=payments")
        assert response.status_code == 200
        assert "Платежи и донат" in response.text
        assert "Данные игрока" not in response.text
        assert 'section=payments" class="account-sidebar-link is-active"' in response.text

    def test_profile_page_falls_back_to_overview_for_unknown_section(self):
        app = _make_app(user=_user_mock())
        client = TestClient(app, raise_server_exceptions=False)
        with _patch_repo():
            response = client.get("/account/profile?section=unknown")
        assert response.status_code == 200
        assert "Личный кабинет" in response.text
        assert 'section=overview" class="account-sidebar-link is-active"' in response.text

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
