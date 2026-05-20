import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from src.frontend.features.feedback.routes.pages import router


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


def _user_mock(*, tester_status="approved"):
    return MagicMock(
        id=uuid.uuid4(),
        email="tester@example.com",
        is_active=True,
        is_superuser=False,
        tester_status=tester_status,
        tester_approved_at=datetime(2026, 5, 10),
        created_at=datetime(2026, 5, 1),
    )


@pytest.mark.unit
class TestFeedbackRoutes:
    def test_feedback_list_requires_tester_status(self):
        app = _make_app(user=_user_mock(tester_status="none"))
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/account/feedback", follow_redirects=False)
        assert response.status_code == 303
        assert "/account/profile" in response.headers["location"]

    def test_feedback_list_redirects_anonymous(self):
        app = _make_app(user=None)
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/account/feedback", follow_redirects=False)
        assert response.status_code == 303
        assert "/login" in response.headers["location"]

    @patch("src.frontend.features.feedback.routes.pages.get_db")
    def test_feedback_new_get_renders_form(self, mock_get_db):
        app = _make_app(user=_user_mock())
        mock_get_db.return_value = AsyncMock()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/account/feedback/new")
        assert response.status_code == 200

    @patch("src.frontend.features.feedback.routes.pages.get_db")
    def test_feedback_new_post_creates_and_redirects(self, mock_get_db):
        user = _user_mock()
        app = _make_app(user=user)

        mock_session = AsyncMock()
        mock_get_db.return_value = mock_session

        mock_feedback = MagicMock(id=1, type="bug", title="Test", body="Test body", status="new")

        with patch(
            "src.frontend.features.feedback.routes.pages.FeedbackRepository",
        ) as MockRepo:
            mock_repo = AsyncMock()
            mock_repo.create = AsyncMock(return_value=mock_feedback)
            mock_repo.commit = AsyncMock()
            MockRepo.return_value = mock_repo

            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/account/feedback/new",
                data={"type": "bug", "title": "Test bug report", "body": "This is a test bug report body"},
                follow_redirects=False,
            )

        assert response.status_code == 303
        assert "/account/feedback" in response.headers["location"]
